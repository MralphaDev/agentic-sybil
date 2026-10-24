
from typing import TypedDict

import networkx as nx


class NoiseEvidence(TypedDict):
    direct_incoming_sybil: list[str]
    direct_outgoing_sybil: list[str]
    nearest_verified_sybil: str | None
    shortest_path_to_sybil: list[str] | None
    hops_to_sybil: int | None


def interpret_noise_wallets(
    agg_graph: nx.DiGraph,
    noise_wallets: set[str],
    verified_sybil_wallets: set[str],
    max_hops: int = 3,
) -> dict[str, NoiseEvidence]:
    """Find direct and short-path connections to verified Sybil wallets."""

    if max_hops < 1:
        raise ValueError("max_hops must be at least 1.")

    graph_nodes = set(agg_graph.nodes)
    verified_in_graph = verified_sybil_wallets & graph_nodes
    undirected_graph = agg_graph.to_undirected()

    results: dict[str, NoiseEvidence] = {}

    for wallet in sorted(noise_wallets):
        if wallet not in graph_nodes:
            continue

        direct_incoming = sorted(
            set(agg_graph.predecessors(wallet)) & verified_in_graph
        )

        direct_outgoing = sorted(
            set(agg_graph.successors(wallet)) & verified_in_graph
        )

        nearest_sybil: str | None = None
        shortest_path: list[str] | None = None
        shortest_hops: int | None = None

        for sybil_wallet in sorted(verified_in_graph):
            if wallet == sybil_wallet:
                continue

            try:
                path = nx.shortest_path(
                    undirected_graph,
                    source=wallet,
                    target=sybil_wallet,
                )
            except nx.NetworkXNoPath:
                continue

            hops = len(path) - 1

            if hops > max_hops:
                continue

            if shortest_hops is None or hops < shortest_hops:
                nearest_sybil = sybil_wallet
                shortest_path = path
                shortest_hops = hops

            if hops == 1:
                break

        results[wallet] = {
            "direct_incoming_sybil": direct_incoming,
            "direct_outgoing_sybil": direct_outgoing,
            "nearest_verified_sybil": nearest_sybil,
            "shortest_path_to_sybil": shortest_path,
            "hops_to_sybil": shortest_hops,
        }

    return results
