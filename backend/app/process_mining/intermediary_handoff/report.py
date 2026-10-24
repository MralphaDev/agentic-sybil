from __future__ import annotations

from typing import Any

import pandas as pd

from .predecessor import find_predecessor


def _time_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def build_compact_report(
    raw_chains: list[list[dict[str, Any]]],
    inbound_index: dict[str, list[dict[str, Any]]],
    seller_count: int,
) -> dict[str, Any]:
    """
    Format the API response with only summary and chains.

    Signatures are used internally to deduplicate chains but are not exposed.
    """
    formatted_chains: list[dict[str, Any]] = []
    seen_chain_keys: set[tuple[Any, ...]] = set()

    for path in raw_chains:
        chain_key = tuple(
            (
                edge.get("_signature"),
                edge["from"],
                edge["to"],
                edge["time"],
                str(edge["amount"]),
            )
            for edge in path
        )

        if chain_key in seen_chain_keys:
            continue
        seen_chain_keys.add(chain_key)

        first_intermediary = path[0]["from"]
        predecessor_edge = find_predecessor(
            first_intermediary=first_intermediary,
            first_transfer_time=path[0]["time"],
            inbound_index=inbound_index,
        )

        display_transfers: list[dict[str, Any]] = []

        if predecessor_edge is not None:
            display_transfers.append({
                "from": predecessor_edge["from"],
                "to": predecessor_edge["to"],
                "amount": predecessor_edge["amount"],
                "time": _time_string(predecessor_edge["time"]),
            })

        for edge in path:
            display_transfers.append({
                "from": edge["from"],
                "to": edge["to"],
                "amount": edge["amount"],
                "time": _time_string(edge["time"]),
            })

        formatted_chains.append({
            "chain_id": f"CHAIN_{len(formatted_chains) + 1}",
            "predecessor": (
                predecessor_edge["from"]
                if predecessor_edge is not None
                else None
            ),
            "transfers": display_transfers,
        })

    return {
        "summary": {
            "chains_detected": len(formatted_chains),
            "seller_count": seller_count,
        },
        "chains": formatted_chains,
    }
