import json
from pathlib import Path

import pandas as pd


from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.variant.variant_analysis import analyze_variants
from app.process_mining.variant.variant_clustering import cluster_variants
from app.process_mining.variant.variant_timing import analyze_variant_timing
from app.process_mining.dfg.dfg_analysis import discover_dfg
from app.process_mining.variant.variant_top_analysis import analyze_top_variants
from app.process_mining.variant.variant_sell_analysis import analyze_variant_sells
from app.process_mining.intermediary_analysis.intermediary_analysis import (
    get_intermediary,
)
from app.process_mining.intermediary_analysis.coordinated_intermediary_analysis import (
    get_coordinated_intermediary,
)
from app.process_mining.dfg.stochastic_dfg_analysis import (
    add_transition_probabilities,
)
from app.process_mining.intermediary_analysis.wallet_support_analysis import (
    analyze_intermediary_support,
    analyze_seller_behavior,
)
from app.process_mining.intermediary_handoff.analyzer import (
    analyze_intermediary_handoffs,
)
from app.process_mining.wallet_age_distribution.first_activity_concentration import (
    analyze_first_activity_concentration,
)

def run_process_mining(
    events: list[dict],
    target_token_mint: str,
) -> dict:
    if not events:
        print("No events found.")
        return {}

    df = pd.DataFrame(events)

    df["action"] = df.apply(
        lambda row: map_event_action(
            row.to_dict(),
            target_token_mint=target_token_mint,
        ),
        axis=1,
    )
    #Before dust filtering, analyze first activity concentration since dust filtering may remove some wallets and skew the results.
    first_activity_result = analyze_first_activity_concentration(df)
    
    # Keep spam dusting filtering in the analysis layer.
    df = df.loc[
        ~(
            df["type"].eq("transfer")
            & (
                pd.to_numeric(df["amount"], errors="coerce")
                < 0.001
            )
        )
    ].copy()

    if df.empty:
        print("No events remain after filtering.")
        return {}

    df["case:concept:name"] = df["wallet_address"]
    df["concept:name"] = df["action"]
    df["time:timestamp"] = pd.to_datetime(
        df["event_time"],
        utc=True,
    )
    


    dfg_result = discover_dfg(df)
    # Convert the regular DFG into a stochastic DFG.
    # Each edge now includes its conditional transition probability.
    stochastic_dfg_result = add_transition_probabilities(
        dfg_result
    )
    variant_data = analyze_variants(df)
    
    top_variants_result = analyze_top_variants(
        df,
        top_n=30,
    )
    
    sell_analysis = analyze_variant_sells(
        df,
        variant_data["wallet_variants"],
    )

    clustering_result = cluster_variants(
        variant_data["variants"]
    )
    
    intermediary_result = get_intermediary(df)

    coordinated_intermediary_result = get_coordinated_intermediary(
        df,
        max_gap_minutes=5,
    )
    
    # Reuse the wallets identified by existing intermediary modules.
    intermediary_wallets = {
        item["wallet_address"]
        for item in intermediary_result["wallets"]
    }

    coordinated_wallets = {
        item["wallet_address"]
        for item in coordinated_intermediary_result["wallets"]
    }

    # Analyze counterparties for both intermediary groups.
    intermediary_support_result = analyze_intermediary_support(
        df,
        intermediary_wallets,
    )

    coordinated_support_result = analyze_intermediary_support(
        df,
        coordinated_wallets,
    )

    # Reuse the existing variant sell analysis to identify sellers.
    seller_wallets = {
        wallet
        for variant in sell_analysis["variants"]
        for wallet in variant["sell_wallets"]
    }
    

    # Analyze target-token handoffs between intermediaries and sellers.
    intermediary_handoff_result = analyze_intermediary_handoffs(
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

    seller_behavior_result = analyze_seller_behavior(
        df,
        seller_wallets,
    )
    
    

    
    '''timing_result = analyze_variant_timing(
        df,
        variant_data["wallet_variants"],
    )'''
    

    output = {
        "dfg": dfg_result,
        "stochastic_dfg": stochastic_dfg_result,
        "first_activity_concentration": first_activity_result,
        "wallet_variants": variant_data["wallet_variants"],
        "variants": variant_data["variants"],
        "top_variants": top_variants_result,
        #"variant_timing": timing_result,
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

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Events: {len(df)}")
    print(f"Wallets: {df['wallet_address'].nunique()}")
    print(f"Unique variants: {len(variant_data['variants'])}")
    print(f"Clusters: {len(clustering_result['clusters'])}")
    print(f"DFG image: {Path('dfg.png').resolve()}")
    print(f"JSON output: {output_path.resolve()}")

    return output
