from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


def prepare_target_transfers(
    data: pd.DataFrame,
    target_token_mint: str,
) -> pd.DataFrame:
    """Select and normalize observed target-token transfer events."""
    transfers = data.loc[
        data["mint"].eq(target_token_mint)
        & data["action"].eq("transfer_target_token")
        & data["from_user_address"].notna()
        & data["to_user_address"].notna()
    ].copy()

    transfers = transfers.loc[
        transfers["from_user_address"].ne("")
        & transfers["to_user_address"].ne("")
        & transfers["from_user_address"].ne("<NA>")
        & transfers["to_user_address"].ne("<NA>")
        & transfers["from_user_address"].ne(transfers["to_user_address"])
    ].copy()

    amount_columns = [
        column
        for column in ("amount", "to_amount", "from_amount")
        if column in transfers.columns
    ]

    def get_amount(row: pd.Series) -> Any:
        for column in amount_columns:
            value = row[column]
            if value is None or pd.isna(value):
                continue
            if hasattr(value, "item"):
                value = value.item()
            if isinstance(value, (int, float, str)):
                return value
            return str(value)
        return None

    transfers["_amount"] = transfers.apply(get_amount, axis=1)

    dedup_columns = [
        column
        for column in (
            "signature",
            "event_time",
            "from_user_address",
            "to_user_address",
            "mint",
            "_amount",
        )
        if column in transfers.columns
    ]
    transfers = transfers.drop_duplicates(
        subset=dedup_columns,
        keep="first",
    )

    transfers = transfers.sort_values(
        ["event_time", "signature"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    events: list[dict[str, Any]] = []
    for _, row in transfers.iterrows():
        events.append({
            "from": str(row["from_user_address"]),
            "to": str(row["to_user_address"]),
            "amount": row["_amount"],
            "time": row["event_time"],
            # Internal-only key for deduplication; never emitted in the report.
            "_signature": (
                None if pd.isna(row["signature"]) else str(row["signature"])
            ),
        })

    # Return records in a DataFrame so the analyzer can use a consistent
    # event representation for both graph search and predecessor lookup.
    return pd.DataFrame(
        events,
        columns=["from", "to", "amount", "time", "_signature"],
    )


def build_handoff_graph(
    transfer_events: list[dict[str, Any]],
    intermediary_wallets: set[str],
    seller_wallets: set[str],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Build edges from intermediaries to known intermediaries or sellers."""
    known_wallets = intermediary_wallets | seller_wallets

    edges = [
        edge
        for edge in transfer_events
        if edge["from"] in intermediary_wallets
        and edge["to"] in known_wallets
    ]

    edges.sort(
        key=lambda edge: (
            edge["time"],
            edge["from"],
            edge["to"],
        )
    )

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["from"]].append(edge)

    return edges, outgoing


def enumerate_chains(
    outgoing: dict[str, list[dict[str, Any]]],
    intermediary_wallets: set[str],
    seller_wallets: set[str],
    max_gap_minutes: float = 5,
    min_hops: int = 1,
    max_hops: int = 10,
    max_chains: int = 5000,
) -> list[list[dict[str, Any]]]:
    """
    Enumerate time-ordered intermediary handoff paths.

    A direct intermediary -> seller transfer is a one-hop chain.
    Adjacent edges must be no more than max_gap_minutes apart.
    A wallet cannot repeat within a chain.
    """
    max_gap_seconds = max_gap_minutes * 60
    chains: list[list[dict[str, Any]]] = []
    truncated = False

    def save_chain(path: list[dict[str, Any]]) -> None:
        nonlocal truncated

        if len(path) < min_hops:
            return
        if len(chains) >= max_chains:
            truncated = True
            return
        chains.append(path.copy())

    def dfs(
        current_wallet: str,
        path: list[dict[str, Any]],
        visited_wallets: set[str],
    ) -> None:
        nonlocal truncated

        if truncated:
            return

        if len(path) >= max_hops:
            save_chain(path)
            return

        previous_time = path[-1]["time"]
        next_edges = [
            edge
            for edge in outgoing.get(current_wallet, [])
            if edge["time"] >= previous_time
            and (edge["time"] - previous_time).total_seconds()
            <= max_gap_seconds
            and edge["to"] not in visited_wallets
        ]

        if not next_edges:
            save_chain(path)
            return

        for edge in next_edges:
            next_path = path + [edge]

            if edge["to"] in seller_wallets:
                save_chain(next_path)
            else:
                dfs(
                    current_wallet=edge["to"],
                    path=next_path,
                    visited_wallets=visited_wallets | {edge["to"]},
                )

            if truncated:
                return

    for first_wallet in sorted(intermediary_wallets):
        for first_edge in outgoing.get(first_wallet, []):
            if first_edge["to"] in seller_wallets:
                save_chain([first_edge])
            else:
                dfs(
                    current_wallet=first_edge["to"],
                    path=[first_edge],
                    visited_wallets={first_wallet, first_edge["to"]},
                )

            if truncated:
                break
        if truncated:
            break

    return chains
