from typing import Any

from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.ml.similarity_clustering import cluster_wallets


def build_wallet_clustering_tools(context: AnalysisContext):
    def get_clustering_result() -> dict[str, Any]:
        """Compute clustering once and reuse the result from context cache."""
        cache_key = "wallet_clustering_result"

        if cache_key not in context.cache:
            context.cache[cache_key] = cluster_wallets(
                agg_graph=context.aggregated_tx_graph,
                wallet_features=context.wallet_features,
            )

        return context.cache[cache_key]

    @tool
    def find_wallet_clusters(wallet_addresses: list[str]) -> dict[str, Any]:
        """Find the component and HDBSCAN cluster status for up to 10 wallets.

        Reports each wallet as clustered, noise, skipped, or not found.
        Use this to investigate whether wallets belong to the same cluster.
        """
        if not 1 <= len(wallet_addresses) <= 10:
            return {
                "error": "Provide between 1 and 10 wallet addresses."
            }

        wallet_addresses = list(dict.fromkeys(wallet_addresses))
        result = get_clustering_result()

        wallet_status: dict[str, dict[str, Any]] = {}

        for component in result.get("components", []):
            component_id = component["component_id"]

            for cluster_id, wallets in component.get("clusters", {}).items():
                for wallet in wallets:
                    wallet_status[wallet] = {
                        "wallet_address": wallet,
                        "component_id": component_id,
                        "cluster_id": cluster_id,
                        "status": "clustered",
                    }

            for wallet in component.get("noise_wallets", []):
                wallet_status[wallet] = {
                    "wallet_address": wallet,
                    "component_id": component_id,
                    "cluster_id": None,
                    "status": "noise",
                }

            for wallet in component.get("skipped_wallets", []):
                wallet_status[wallet] = {
                    "wallet_address": wallet,
                    "component_id": component_id,
                    "cluster_id": None,
                    "status": "skipped",
                }

        wallets_result = []

        for wallet in wallet_addresses:
            item = wallet_status.get(wallet)

            if item is None:
                item = {
                    "wallet_address": wallet,
                    "component_id": None,
                    "cluster_id": None,
                    "status": "not_found",
                }

            wallets_result.append(item)

        return {
            "wallet_count": len(wallets_result),
            "wallets": wallets_result,
        }

    return [find_wallet_clusters]