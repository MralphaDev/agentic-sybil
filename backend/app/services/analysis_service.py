import json
import time
from typing import Callable, Any

import networkx as nx
from fastapi.encoders import jsonable_encoder

from app.database.queries import get_wallet_events
from app.database.queries import get_wallet_profile_addresses
from app.database.features.write_feature import write_wallet_features
from app.process_mining.orchestrator import run_process_mining
from app.features.compute_wallet_feature import compute_wallet_features
from app.transaction_info_helper.transfer_extractor import extract_wallet_transfers
from app.transaction_info_helper.swap_extractor import extract_wallet_swaps
from app.transaction_graph.aggregated_tx_graph.builder import build_aggregated_tx_graph
from app.transaction_graph.first_fund_graph import build_first_fund_graph
from app.ml.similarity_clustering import cluster_wallets
from app.ml.noise_interpretation import interpret_noise_wallets
from app.features.normalize_wallet_features import normalize_wallet_features
from app.agent.context import AnalysisContext
from app.agent.orchestrator import run_agent_investigation


def timed_step(name: str, func: Callable, *args, **kwargs) -> Any:
    """Execute a function and print its elapsed time, even if it fails."""
    start = time.perf_counter()

    try:
        return func(*args, **kwargs)
    finally:
        elapsed = time.perf_counter() - start
        print(f"[TIMING] {name}: {elapsed:.4f}s", flush=True)


def execute_analysis(target_token_mint: str) -> dict:
    total_start = time.perf_counter()

    try:
        # 1. Load data
        events = timed_step(
            "01_get_wallet_events",
            get_wallet_events,
        )

        profile_wallets = timed_step(
            "02_get_wallet_profile_addresses",
            get_wallet_profile_addresses,
        )

        # 2. Extract transaction information
        wallet_transfers = timed_step(
            "03_extract_wallet_transfers",
            extract_wallet_transfers,
            events,
        )

        wallet_swaps = timed_step(
            "04_extract_wallet_swaps",
            extract_wallet_swaps,
            events,
        )

        # 3. Compute and normalize wallet features
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

        # 4. Build transaction graphs
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

        # 5. Cluster wallets
        '''clustering_result = timed_step(
            "09_cluster_wallets",
            cluster_wallets,
            agg_graph=agg_graph,
            wallet_features=wallet_features,
        )'''

        # 6. Interpret noise wallets (currently disabled)
        verified_sybil_wallets: set[str] = set()

        # noise_result = timed_step(
        #     "10_interpret_noise_wallets",
        #     interpret_noise_wallets,
        #     agg_graph=agg_graph,
        #     noise_wallets=clustering_result["noise_wallets"],
        #     verified_sybil_wallets=verified_sybil_wallets,
        # )

        # 7. Persist computed features
        written_count = timed_step(
            "11_write_wallet_features",
            write_wallet_features,
            wallet_features,
        )

        # 8. Process mining (currently disabled)
        # process_mining_result = timed_step(
        #     "12_run_process_mining",
        #     run_process_mining,
        #     events=events,
        #     target_token_mint=target_token_mint,
        # )

        # 9. Build investigation context
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

        # 10. Run AI investigation
        investigation_result = timed_step(
            "14_run_agent_investigation",
            run_agent_investigation,
            context,
        )

        # 11. Serialize graphs
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

        # 12. Write graph JSON files
        def save_json(path: str, data: dict) -> None:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
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

        # 13. Return results
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

            "investigation": investigation_result,
        }

    finally:
        total_elapsed = time.perf_counter() - total_start
        print(
            f"[TIMING] execute_analysis TOTAL: {total_elapsed:.4f}s",
            flush=True,
        )