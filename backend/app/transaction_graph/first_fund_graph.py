import networkx as nx
from typing import Any


def build_first_fund_graph(
    wallet_features: dict[str, dict[str, Any]],
    profile_wallets: list[str] | set[str],
) -> nx.DiGraph:
    """Build a first-funding graph from wallet profiles."""

    graph = nx.DiGraph()

    # Add all profile wallets first.
    for wallet in profile_wallets:
        feature = wallet_features.get(wallet, {})

        graph.add_node(
            wallet,
            profile_known=True,
            first_fund_time=feature.get("first_fund_time"),
            first_fund_amount=feature.get("first_fund_amount"),
            first_fund_mint=feature.get("first_fund_mint"),
            in_degree=feature.get("in_degree"),
            out_degree=feature.get("out_degree"),
        )

    # Add first-funding relationships only between profile wallets.
    profile_wallet_set = set(profile_wallets)

    for wallet in profile_wallet_set:
        feature = wallet_features.get(wallet, {})
        first_funder = feature.get("first_funder")

        if (
            not first_funder
            or wallet == first_funder
            or first_funder not in profile_wallet_set
        ):
            continue

        graph.add_edge(
            first_funder,
            wallet,
            relationship="first_fund",
            event_time=feature.get("first_fund_time"),
            amount=feature.get("first_fund_amount"),
            token=feature.get("first_fund_mint"),
        )

    return graph