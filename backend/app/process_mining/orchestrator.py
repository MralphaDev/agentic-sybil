import json
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from app.agent.sse_manager import get_current_event_callback
from app.process_mining.dfg.dfg_analysis import discover_dfg
from app.process_mining.dfg.stochastic_dfg_analysis import (
    add_transition_probabilities,
)
from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.intermediary_analysis.coordinated_intermediary_analysis import (
    get_coordinated_intermediary,
)
from app.process_mining.intermediary_analysis.intermediary_analysis import (
    get_intermediary,
)
from app.process_mining.intermediary_analysis.wallet_support_analysis import (
    analyze_intermediary_support,
    analyze_seller_behavior,
)
from app.process_mining.intermediary_handoff.analyzer import (
    analyze_intermediary_handoffs,
)
from app.process_mining.variant.variant_analysis import analyze_variants
from app.process_mining.variant.variant_clustering import cluster_variants
from app.process_mining.variant.variant_sell_analysis import analyze_variant_sells
from app.process_mining.variant.variant_top_analysis import analyze_top_variants
from app.process_mining.wallet_age_distribution.first_activity_concentration import (
    analyze_first_activity_concentration,
)


PROCESS_MINING_STEPS: dict[str, tuple[str, str]] = {
    "12_01_map_event_actions": (
        "Mapping wallet actions",
        "Translating raw on-chain events into process-mining actions.",
    ),
    "12_02_first_activity_concentration": (
        "Analyzing first-activity concentration",
        "Checking whether wallet activity is concentrated in suspicious time windows.",
    ),
    "12_03_filter_dust_transfers": (
        "Filtering dust transfers",
        "Removing tiny transfers that may distort behavioral patterns.",
    ),
    "12_04_prepare_event_log": (
        "Preparing process event log",
        "Preparing wallet cases, action labels, and event timestamps.",
    ),
    "12_05_discover_dfg": (
        "Discovering directly-follows graph",
        "Identifying which wallet actions directly follow one another.",
    ),
    "12_06_transition_probabilities": (
        "Calculating transition probabilities",
        "Estimating the likelihood of transitions between actions.",
    ),
    "12_07_analyze_variants": (
        "Analyzing wallet variants",
        "Extracting distinct action sequences for individual wallets.",
    ),
    "12_08_top_variants": (
        "Extracting top variants",
        "Ranking the most common wallet action sequences.",
    ),
    "12_09_variant_sell_analysis": (
        "Analyzing variant sell behavior",
        "Comparing sell activity across wallet behavior variants.",
    ),
    "12_10_cluster_variants": (
        "Clustering behavior variants",
        "Grouping similar action sequences into behavioral clusters.",
    ),
    "12_11_intermediary_analysis": (
        "Analyzing intermediary wallets",
        "Identifying wallets that may relay assets between participants.",
    ),
    "12_12_coordinated_intermediaries": (
        "Analyzing coordinated intermediaries",
        "Searching for intermediary activity occurring within short time gaps.",
    ),
    "12_13_intermediary_support": (
        "Analyzing intermediary counterparties",
        "Examining the counterparties associated with intermediary wallets.",
    ),
    "12_14_coordinated_support": (
        "Analyzing coordinated counterparties",
        "Examining the counterparties of coordinated intermediary wallets.",
    ),
    "12_15_handoff_analysis": (
        "Analyzing token handoffs",
        "Tracing potential transfers from intermediary wallets to sellers.",
    ),
    "12_16_seller_behavior": (
        "Analyzing seller behavior",
        "Summarizing the behavior of wallets identified as sellers.",
    ),
    "12_17_write_results": (
        "Saving Process Mining results",
        "Writing the Process Mining output to a JSON file.",
    ),
}


def _emit_stage(
    step: str,
    state: str,
    elapsed_seconds: float | None = None,
) -> None:
    callback = get_current_event_callback()
    if callback is None:
        return

    title, detail = PROCESS_MINING_STEPS.get(
        step,
        (step.replace("_", " ").title(), "Processing this analysis step."),
    )

    payload: dict[str, Any] = {
        "step": step,
        "title": title,
        "detail": detail,
        "state": state,
    }

    if elapsed_seconds is not None:
        payload["elapsed_seconds"] = round(elapsed_seconds, 3)

    try:
        callback("stage", payload)
    except Exception as exc:
        print(f"[PROGRESS] Failed to emit stage {step}: {exc}", flush=True)


def _timed_step(
    name: str,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    start = time.perf_counter()
    _emit_stage(name, "running")

    try:
        result = func(*args, **kwargs)
    except Exception:
        elapsed = time.perf_counter() - start
        print(
            f"[TIMING] {name}: FAILED after {elapsed:.4f}s",
            flush=True,
        )
        _emit_stage(name, "failed", elapsed)
        raise

    elapsed = time.perf_counter() - start
    print(f"[TIMING] {name}: {elapsed:.4f}s", flush=True)
    _emit_stage(name, "finished", elapsed)
    return result


def run_process_mining(
    events: list[dict],
    target_token_mint: str,
) -> dict:
    if not events:
        print("No events found.")
        return {}

    df = pd.DataFrame(events)

    df["action"] = _timed_step(
        "12_01_map_event_actions",
        lambda: df.apply(
            lambda row: map_event_action(
                row.to_dict(),
                target_token_mint=target_token_mint,
            ),
            axis=1,
        ),
    )

    # Analyze before dust filtering because filtering may remove wallets
    # and skew the first-activity distribution.
    first_activity_result = _timed_step(
        "12_02_first_activity_concentration",
        analyze_first_activity_concentration,
        df,
    )

    df = _timed_step(
        "12_03_filter_dust_transfers",
        lambda: df.loc[
            ~(
                df["type"].eq("transfer")
                & (
                    pd.to_numeric(df["amount"], errors="coerce")
                    < 0.001
                )
            )
        ].copy(),
    )

    if df.empty:
        print("No events remain after filtering.")
        return {
            "first_activity_concentration": first_activity_result,
        }

    def prepare_event_log() -> pd.DataFrame:
        prepared = df.copy()
        prepared["case:concept:name"] = prepared["wallet_address"]
        prepared["concept:name"] = prepared["action"]
        prepared["time:timestamp"] = pd.to_datetime(
            prepared["event_time"],
            utc=True,
        )
        return prepared

    df = _timed_step(
        "12_04_prepare_event_log",
        prepare_event_log,
    )

    dfg_result = _timed_step(
        "12_05_discover_dfg",
        discover_dfg,
        df,
    )

    stochastic_dfg_result = _timed_step(
        "12_06_transition_probabilities",
        add_transition_probabilities,
        dfg_result,
    )

    variant_data = _timed_step(
        "12_07_analyze_variants",
        analyze_variants,
        df,
    )

    top_variants_result = _timed_step(
        "12_08_top_variants",
        analyze_top_variants,
        df,
        top_n=30,
    )

    sell_analysis = _timed_step(
        "12_09_variant_sell_analysis",
        analyze_variant_sells,
        df,
        variant_data["wallet_variants"],
    )

    clustering_result = _timed_step(
        "12_10_cluster_variants",
        cluster_variants,
        variant_data["variants"],
    )

    intermediary_result = _timed_step(
        "12_11_intermediary_analysis",
        get_intermediary,
        df,
    )

    coordinated_intermediary_result = _timed_step(
        "12_12_coordinated_intermediaries",
        get_coordinated_intermediary,
        df,
        max_gap_minutes=5,
    )

    intermediary_wallets = {
        item["wallet_address"]
        for item in intermediary_result["wallets"]
    }

    coordinated_wallets = {
        item["wallet_address"]
        for item in coordinated_intermediary_result["wallets"]
    }

    intermediary_support_result = _timed_step(
        "12_13_intermediary_support",
        analyze_intermediary_support,
        df,
        intermediary_wallets,
    )

    coordinated_support_result = _timed_step(
        "12_14_coordinated_support",
        analyze_intermediary_support,
        df,
        coordinated_wallets,
    )

    seller_wallets = {
        wallet
        for variant in sell_analysis["variants"]
        for wallet in variant["sell_wallets"]
    }

    intermediary_handoff_result = _timed_step(
        "12_15_handoff_analysis",
        analyze_intermediary_handoffs,
        df=df,
        intermediary_wallets=(
            intermediary_wallets | coordinated_wallets
        ),
        seller_wallets=seller_wallets,
        target_token_mint=target_token_mint,
        max_gap_minutes=5,
        max_hops=10,
        max_chains=5000,
        max_actions_after_receive=2,
    )

    seller_behavior_result = _timed_step(
        "12_16_seller_behavior",
        analyze_seller_behavior,
        df,
        seller_wallets,
    )

    output = {
        "dfg": dfg_result,
        "stochastic_dfg": stochastic_dfg_result,
        "first_activity_concentration": first_activity_result,
        "wallet_variants": variant_data["wallet_variants"],
        "variants": variant_data["variants"],
        "top_variants": top_variants_result,
        "clustering": clustering_result,
        "sell_analysis": sell_analysis,
        "seller_behavior": seller_behavior_result,
        "intermediary_analysis": intermediary_result,
        "coordinated_intermediary_analysis": coordinated_intermediary_result,
        "intermediary_handoff_analysis": intermediary_handoff_result,
        "intermediary_support": intermediary_support_result,
        "coordinated_support": coordinated_support_result,
    }

    output_path = Path("process_mining_analysis.json")

    def write_output() -> None:
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                output,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

    _timed_step(
        "12_17_write_results",
        write_output,
    )

    print(f"Events: {len(df)}")
    print(f"Wallets: {df['wallet_address'].nunique()}")
    print(f"Unique variants: {len(variant_data['variants'])}")
    print(f"Clusters: {len(clustering_result['clusters'])}")
    print(f"DFG image: {Path('dfg.png').resolve()}")
    print(f"JSON output: {output_path.resolve()}")

    return output