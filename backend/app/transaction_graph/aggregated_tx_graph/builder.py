
from typing import Any

import networkx as nx

from app.transaction_graph.aggregated_tx_graph.aggregator import aggregate_transfers


def build_aggregated_tx_graph(
    wallet_transfers: dict[str, dict[str, list[dict[str, Any]]]],
    profile_wallets: set[str],
) -> nx.DiGraph:
    """Build a directed aggregated transaction graph from profiled wallets."""

    aggregated = aggregate_transfers(
        wallet_transfers,
        profile_wallets,
    )

    graph = nx.DiGraph()

    # Add all wallet profiles, including wallets without transfer edges.
    graph.add_nodes_from(profile_wallets)

    # Add aggregated transfer relationships.
    for (sender, receiver), edge_data in aggregated.items():
        graph.add_edge(
            sender,
            receiver,
            transfer_count=edge_data["transfer_count"],
            unique_tx_count=edge_data["unique_tx_count"],
            signatures=edge_data["signatures"],
            token_mints=edge_data["token_mints"],
            amount_by_mint=edge_data["amount_by_mint"],
            first_transfer_time=edge_data["first_transfer_time"],
            last_transfer_time=edge_data["last_transfer_time"],
        )

    return graph
