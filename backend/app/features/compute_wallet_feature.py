from typing import Any


def compute_wallet_features(
    events: list[dict[str, Any]],
    wallet_transfers: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, dict[str, Any]]:
    """Compute features for each wallet."""

    wallet_signatures: dict[str, set[str]] = {}

    # Count unique transactions for each wallet.
    for event in events:
        wallet = event.get("wallet_address")
        signature = event.get("signature")

        if not wallet:
            continue

        if wallet not in wallet_signatures:
            wallet_signatures[wallet] = set()

        if signature:
            wallet_signatures[wallet].add(signature)

    features: dict[str, dict[str, Any]] = {}

    for wallet, signatures in wallet_signatures.items():
        transfers = wallet_transfers.get(
            wallet,
            {"incoming": [], "outgoing": []},
        )

        incoming = transfers["incoming"]
        outgoing = transfers["outgoing"]
        
        # Find the earliest incoming transfer.
        first_fund = min(
            (
                transfer
                for transfer in incoming
                if transfer.get("event_time") is not None
                and transfer.get("amount") is not None
            ),
            key=lambda transfer: transfer["event_time"],
            default=None,
        )
        
        # Count unique counterparties, not transfer events.
        in_degree = len({
            transfer["from_wallet"]
            for transfer in incoming
            if transfer.get("from_wallet")
            and transfer["from_wallet"] != wallet
        })

        out_degree = len({
            transfer["to_wallet"]
            for transfer in outgoing
            if transfer.get("to_wallet")
            and transfer["to_wallet"] != wallet
        })

        features[wallet] = {
            "first_fund_time": (
                first_fund["event_time"] if first_fund else None
            ),
            "first_fund_amount": (
                first_fund["amount"] if first_fund else None
            ),
            "first_fund_mint": (
                (first_fund["mint"] or "native transfer")
                if first_fund
                else None
            ),
            "first_funder": (
                first_fund["from_wallet"] if first_fund else None
            ),
            "total_tx_count": len(signatures),
            "in_degree": in_degree,
            "out_degree": out_degree,
        }

    return features