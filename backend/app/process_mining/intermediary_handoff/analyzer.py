
from __future__ import annotations

from typing import Any

import pandas as pd

from .detection import detect_behavioral_intermediaries
from .graph import build_handoff_graph, enumerate_chains, prepare_target_transfers
from .predecessor import build_inbound_transfer_index
from .report import build_compact_report
from .validation import validate_inputs


def analyze_intermediary_handoffs(
    df: pd.DataFrame,
    intermediary_wallets: set[str],
    seller_wallets: set[str],
    target_token_mint: str,
    max_gap_minutes: float = 5,
    min_hops: int = 1,
    max_hops: int = 10,
    max_chains: int = 5000,
    max_actions_after_receive: int = 2,
) -> dict[str, Any]:
    """
    Analyze target-token handoff chains and return a compact report.

    The complete per-wallet action sequence is used to detect behavioral
    intermediaries. Only target-token transfers are used to build the graph.
    Consecutive graph edges must be within max_gap_minutes.

    The predecessor is the most recent observed inbound transfer of the
    target token to the first intermediary before that intermediary's first
    transfer in the chain. This is an observed candidate, not proof of
    token provenance.
    """
    validate_inputs(
        df=df,
        target_token_mint=target_token_mint,
        max_gap_minutes=max_gap_minutes,
        min_hops=min_hops,
        max_hops=max_hops,
        max_chains=max_chains,
        max_actions_after_receive=max_actions_after_receive,
    )

    sellers = seller_wallets
    known_intermediaries = intermediary_wallets - sellers

    behavioral_intermediaries = detect_behavioral_intermediaries(
        data=df,
        target_token_mint=target_token_mint,
        max_actions_after_receive=max_actions_after_receive,
    )

    all_intermediaries = (
        known_intermediaries | behavioral_intermediaries
    ) - sellers

    target_transfers = prepare_target_transfers(
        data=df,
        target_token_mint=target_token_mint,
    )

    all_transfer_events = target_transfers.to_dict("records")

    graph_edges, outgoing = build_handoff_graph(
        transfer_events=all_transfer_events,  # pyright: ignore[reportArgumentType]
        intermediary_wallets=all_intermediaries,
        seller_wallets=sellers,
    )

    raw_chains = enumerate_chains(
        outgoing=outgoing,
        intermediary_wallets=all_intermediaries,
        seller_wallets=sellers,
        max_gap_minutes=max_gap_minutes,
        min_hops=min_hops,
        max_hops=max_hops,
        max_chains=max_chains,
    )

    inbound_index = build_inbound_transfer_index(
        all_transfer_events # pyright: ignore[reportArgumentType]
    )  

    return build_compact_report(
        raw_chains=raw_chains,
        inbound_index=inbound_index,
        seller_count=len(sellers),
    )
