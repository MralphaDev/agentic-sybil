
from typing import Any, TypedDict

import hdbscan
import networkx as nx
import numpy as np

from app.ml.similarity import behavior_vector_sim


class ComponentClusteringResult(TypedDict):
    component_id: int
    size: int
    valid_wallet_count: int
    clusters: dict[int, list[str]]
    noise_wallets: list[str]
    skipped_wallets: list[str]


class ClusteringResult(TypedDict):
    components: list[ComponentClusteringResult]
    component_count: int


def cluster_wallets(
    agg_graph: nx.DiGraph,
    wallet_features: dict[str, dict[str, Any]],
    min_cluster_size: int = 4,
) -> ClusteringResult:
    """Cluster wallets independently within weakly connected components."""

    if min_cluster_size < 2:
        raise ValueError("min_cluster_size must be at least 2.")

    components: list[ComponentClusteringResult] = []

    # Sort components for reproducible component IDs.
    component_nodes_list = sorted(
        nx.weakly_connected_components(agg_graph),
        key=lambda nodes: min(nodes) if nodes else "",
    )

    for component_id, component_nodes in enumerate(component_nodes_list):
        wallets = sorted(component_nodes)

        valid_wallets: list[str] = []
        skipped_wallets: list[str] = []

        for wallet in wallets:
            feature = wallet_features.get(wallet)

            if feature is None:
                skipped_wallets.append(wallet)
                continue

            tx_count = feature.get("total_tx_count")
            amount = feature.get("first_fund_amount")
            fund_time = feature.get("first_fund_time")

            if (
                not isinstance(tx_count, int)
                or isinstance(tx_count, bool)
                or tx_count < 0
            ):
                skipped_wallets.append(wallet)
                continue

            if amount is None and fund_time is None:
                skipped_wallets.append(wallet)
                continue

            if amount is not None and (
                not isinstance(amount, (int, float))
                or isinstance(amount, bool)
                or not np.isfinite(amount)
                or amount < 0
            ):
                skipped_wallets.append(wallet)
                continue

            if fund_time is not None and not hasattr(
                fund_time, "utcoffset"
            ):
                skipped_wallets.append(wallet)
                continue

            valid_wallets.append(wallet)

        clusters: dict[int, list[str]] = {}
        component_noise: list[str] = []

        if len(valid_wallets) < min_cluster_size:
            component_noise = valid_wallets.copy()
        else:
            size = len(valid_wallets)
            distance_matrix = np.zeros(
                (size, size),
                dtype=np.float64,
            )

            for i in range(size):
                for j in range(i + 1, size):
                    similarity = behavior_vector_sim(
                        wallet_features[valid_wallets[i]],
                        wallet_features[valid_wallets[j]],
                    )

                    distance = 1.0 - similarity
                    distance_matrix[i, j] = distance
                    distance_matrix[j, i] = distance

            model = hdbscan.HDBSCAN(
                metric="precomputed",
                min_cluster_size=min_cluster_size,
            )

            local_labels = model.fit_predict(distance_matrix)

            for wallet, raw_label in zip(valid_wallets, local_labels):
                label = int(raw_label)

                if label == -1:
                    component_noise.append(wallet)
                    continue

                clusters.setdefault(label, []).append(wallet)

        components.append(
            {
                "component_id": component_id,
                "size": len(wallets),
                "valid_wallet_count": len(valid_wallets),
                "clusters": clusters,
                "noise_wallets": component_noise,
                "skipped_wallets": skipped_wallets,
            }
        )

    return {
        "components": components,
        "component_count": len(components),
    }
