
from typing import Any

import networkx as nx
from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.transaction_info_helper.transfer_connectivity import (
    check_transfer_connectivity,
)


def build_graph_connectivity_tools(context: AnalysisContext):
    @tool
    def find_first_fund_path(
        source_wallet: str,
        target_wallet: str,
    ) -> dict[str, Any]:
        """Find the shortest first-funding path between two wallets.

        Traversal follows the directed first-funding edges:
        source funder -> funded wallet.
        """
        graph = context.first_fund_graph

        if source_wallet not in graph:
            return {
                "connected": False,
                "reason": "source_wallet_not_found",
                "wallets": [],
            }

        if target_wallet not in graph:
            return {
                "connected": False,
                "reason": "target_wallet_not_found",
                "wallets": [],
            }

        try:
            path = nx.shortest_path(
                graph,
                source=source_wallet,
                target=target_wallet,
            )
        except nx.NetworkXNoPath:
            return {
                "connected": False,
                "reason": "no_first_fund_path",
                "wallets": [],
            }

        return {
            "connected": True,
            "path_length": len(path) - 1,
            "wallets": path,
            "relationships": [
                graph.edges[u, v]
                for u, v in zip(path, path[1:])
            ],
        }

    @tool
    def find_transfer_path(
        source_wallet: str,
        target_wallet: str,
    ) -> dict[str, Any]:
        """Find the shortest transfer-connectivity path between two wallets.

        Transfer edges are treated as undirected. Reports whether the path
        involves the target token mint or native SOL.
        """
        return check_transfer_connectivity(
            wallet_transfers=context.wallet_transfers,
            source_wallet=source_wallet,
            target_wallet=target_wallet,
            target_token_mint=context.target_token_mint,
        )

    return [
        find_first_fund_path,
        find_transfer_path,
    ]
