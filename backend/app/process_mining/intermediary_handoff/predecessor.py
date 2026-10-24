from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


def build_inbound_transfer_index(
    transfer_events: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Index all observed target-token transfers by recipient.

    This includes transfers from wallets outside the intermediary/seller
    sets, so a chain's first intermediary can have an unknown predecessor.
    """
    inbound: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for edge in transfer_events:
        inbound[edge["to"]].append(edge)

    for wallet in inbound:
        inbound[wallet].sort(key=lambda edge: edge["time"])

    return dict(inbound)


def find_predecessor(
    first_intermediary: str,
    first_transfer_time: pd.Timestamp,
    inbound_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Find the most recent observed inbound target-token transfer beforehand."""
    candidates = [
        edge
        for edge in inbound_index.get(first_intermediary, [])
        if edge["time"] < first_transfer_time
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda edge: edge["time"])
