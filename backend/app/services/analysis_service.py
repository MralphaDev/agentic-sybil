import asyncio
import json
import time
from typing import Any, Callable

import networkx as nx
from fastapi.encoders import jsonable_encoder

from app.agent.context import AnalysisContext
from app.api.providers.helius.client import HeliusClient
from app.agent.orchestrator import run_agent_investigation
from app.agent.sse_manager import get_current_event_callback
from app.database.features.write_feature import write_wallet_features
from app.database.queries import (
    get_wallet_events,
    get_wallet_profile_addresses,
)
from app.features.compute_wallet_feature import compute_wallet_features
from app.features.normalize_wallet_features import normalize_wallet_features
from app.process_mining.orchestrator import run_process_mining
from app.transaction_graph.aggregated_tx_graph.builder import (
    build_aggregated_tx_graph,
)
from app.transaction_graph.first_fund_graph import build_first_fund_graph
from app.transaction_info_helper.swap_extractor import extract_wallet_swaps
from app.transaction_info_helper.transfer_extractor import (
    extract_wallet_transfers,
)


STEP_LABELS: dict[str, tuple[str, str]] = {
    "01_get_wallet_events": (
        "Loading wallet events",
        "Loading transaction history from the database.",
    ),
    "02_get_wallet_profile_addresses": (
        "Loading wallet profiles",
        "Retrieving wallet addresses for graph analysis.",
    ),
    "03_extract_wallet_transfers": (
        "Extracting wallet transfers",
        "Preparing wallet-to-wallet fund-flow records.",
    ),
    "04_extract_wallet_swaps": (
        "Extracting wallet swaps",
        "Preparing token trading activity.",
    ),
    "05_compute_wallet_features": (
        "Computing wallet features",
        "Calculating behavioral features for each wallet.",
    ),
    "06_normalize_wallet_features": (
        "Normalizing wallet features",
        "Preparing wallet features for downstream analysis.",
    ),
    "07_build_first_fund_graph": (
        "Building first-funding graph",
        "Tracing relationships between initial funding sources and wallets.",
    ),
    "08_build_aggregated_tx_graph": (
        "Building transaction graph",
        "Aggregating wallet-to-wallet transaction relationships.",
    ),
    "11_write_wallet_features": (
        "Saving wallet features",
        "Persisting computed wallet features to the database.",
    ),
    "12_run_process_mining": (
        "Running Process Mining",
        "Analyzing wallet action sequences, variants, and intermediary behavior.",
    ),
    "13_build_analysis_context": (
        "Preparing investigation context",
        "Assembling transaction events, wallet features, and graphs.",
    ),
    "14_run_agent_investigation": (
        "Running agent investigation",
        "The agent is examining evidence and selecting investigation tools.",
    ),
    "15_serialize_first_fund_graph": (
        "Preparing first-funding graph",
        "Converting graph data into a frontend-compatible format.",
    ),
    "16_serialize_aggregated_tx_graph": (
        "Preparing transaction graph",
        "Converting transaction graph data for the frontend.",
    ),
    "17_save_first_fund_graph_json": (
        "Saving first-funding graph",
        "Writing the first-funding graph JSON file.",
    ),
    "18_save_aggregated_tx_graph_json": (
        "Saving transaction graph",
        "Writing the aggregated transaction graph JSON file.",
    ),
}


def emit_stage(
    step: str,
    state: str,
    elapsed_seconds: float | None = None,
) -> None:
    """Send pipeline progress to the active SSE investigation, if any."""
    callback = get_current_event_callback()
    if callback is None:
        return

    title, detail = STEP_LABELS.get(
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
        # Progress reporting must never break the actual analysis.
        print(f"[PROGRESS] Failed to emit stage {step}: {exc}", flush=True)


def timed_step(name: str, func: Callable, *args, **kwargs) -> Any:
    """Execute one pipeline step and publish its running/finished/failed state."""
    start = time.perf_counter()
    emit_stage(name, "running")

    try:
        result = func(*args, **kwargs)
    except Exception:
        elapsed = time.perf_counter() - start
        print(
            f"[TIMING] {name}: FAILED after {elapsed:.4f}s",
            flush=True,
        )
        emit_stage(name, "failed", elapsed)
        raise

    elapsed = time.perf_counter() - start
    print(f"[TIMING] {name}: {elapsed:.4f}s", flush=True)
    emit_stage(name, "finished", elapsed)
    return result


def _get_token_mint_date(token_mint: str) -> str | None:
    """Resolve the earliest parsed event for the mint via Helius."""
    async def fetch() -> str | None:
        async with HeliusClient() as helius:
            return await helius.get_token_mint_date(token_mint)

    # execute_analysis runs in a worker thread from the SSE pipeline.
    return asyncio.run(fetch())


def execute_analysis(target_token_mint: str) -> dict:
    total_start = time.perf_counter()

    try:
        events = timed_step(
            "01_get_wallet_events",
            get_wallet_events,
        )

        profile_wallets = timed_step(
            "02_get_wallet_profile_addresses",
            get_wallet_profile_addresses,
        )

        wallet_transfers = timed_step(
            "03_extract_wallet_transfers",
            extract_wallet_transfers,
            events,
        )

        # Retained to preserve the existing extraction pipeline.
        wallet_swaps = timed_step(
            "04_extract_wallet_swaps",
            extract_wallet_swaps,
            events,
        )

        raw_wallet_features = timed_step(
            "05_compute_wallet_features",
            compute_wallet_features,
            events,
            wallet_transfers,
        )

        wallet_features = timed_step(
            "06_normalize_wallet_features",
            normalize_wallet_features,
            raw_wallet_features,
        )

        first_fund_graph = timed_step(
            "07_build_first_fund_graph",
            build_first_fund_graph,
            wallet_features,
            profile_wallets,
        )

        agg_graph = timed_step(
            "08_build_aggregated_tx_graph",
            build_aggregated_tx_graph,
            wallet_transfers,
            profile_wallets,
        )

        # Clustering remains disabled until the clustering result is needed.
        # verified_sybil_wallets: set[str] = set()

        written_count = timed_step(
            "11_write_wallet_features",
            write_wallet_features,
            wallet_features,
        )

        # Resolve the token's earliest parsed event so temporal evidence is
        # plotted relative to mint creation rather than the full wallet history.
        try:
            token_mint_date = timed_step(
                "10_get_token_mint_date",
                _get_token_mint_date,
                target_token_mint,
            )
        except Exception as exc:
            # Do not fail the entire investigation if Helius cannot resolve the mint.
            print(
                f"[WARN] Could not resolve token mint date; using observed "
                f"wallet activity range instead: {exc}",
                flush=True,
            )
            token_mint_date = None

        # Enabled so the frontend can show each Process Mining substep.
        process_mining_result = timed_step(
            "12_run_process_mining",
            run_process_mining,
            events=events,
            target_token_mint=target_token_mint,
            token_mint_date=token_mint_date,
        )

        context = timed_step(
            "13_build_analysis_context",
            AnalysisContext,
            target_token_mint=target_token_mint,
            events=events,
            profile_wallets=profile_wallets,
            wallet_transfers=wallet_transfers,
            wallet_features=wallet_features,
            first_fund_graph=first_fund_graph,
            aggregated_tx_graph=agg_graph,
        )

        investigation_result = timed_step(
            "14_run_agent_investigation",
            run_agent_investigation,
            context,
        )

        first_fund_data = timed_step(
            "15_serialize_first_fund_graph",
            lambda: jsonable_encoder(
                nx.node_link_data(
                    first_fund_graph,
                    edges="edges",
                )
            ),
        )

        aggregated_tx_data = timed_step(
            "16_serialize_aggregated_tx_graph",
            lambda: jsonable_encoder(
                nx.node_link_data(
                    agg_graph,
                    edges="edges",
                )
            ),
        )

        def save_json(path: str, data: dict) -> None:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

        timed_step(
            "17_save_first_fund_graph_json",
            save_json,
            "first_fund_graph.json",
            first_fund_data,
        )

        timed_step(
            "18_save_aggregated_tx_graph_json",
            save_json,
            "aggregated_tx_graph.json",
            aggregated_tx_data,
        )

        return {
            "wallet_features": wallet_features,
            "first_fund_graph": {
                "nodes": first_fund_graph.number_of_nodes(),
                "edges": first_fund_graph.number_of_edges(),
                "data": first_fund_data,
            },
            "aggregated_tx_graph": {
                "nodes": agg_graph.number_of_nodes(),
                "edges": agg_graph.number_of_edges(),
                "data": aggregated_tx_data,
            },
            "process_mining_result": process_mining_result,
            "investigation": investigation_result,
        }

    finally:
        total_elapsed = time.perf_counter() - total_start
        print(
            f"[TIMING] execute_analysis TOTAL: {total_elapsed:.4f}s",
            flush=True,
        )