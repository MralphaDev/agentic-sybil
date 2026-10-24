from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any


def aggregate_transfers(
    wallet_transfers: dict[str, dict[str, list[dict[str, Any]]]],
    profile_wallets: set[str],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Aggregate transfers between wallets that exist in wallet profiles."""

    aggregated: dict[tuple[str, str], dict[str, Any]] = {}

    for wallet_data in wallet_transfers.values():
        # Each transfer is represented in the sender's outgoing list
        # and the receiver's incoming list. Process outgoing only.
        for transfer in wallet_data.get("outgoing", []):
            sender = transfer.get("from_wallet")
            receiver = transfer.get("to_wallet")

            if not sender or not receiver:
                continue

            # Ignore self-transfers.
            if sender == receiver:
                continue

            # Only include transfers where both wallets have profiles.
            if sender not in profile_wallets or receiver not in profile_wallets:
                continue

            edge_key = (sender, receiver)

            if edge_key not in aggregated:
                aggregated[edge_key] = {
                    "transfer_count": 0,
                    "signatures": set(),
                    "token_mints": set(),
                    "amount_by_mint": defaultdict(Decimal),
                    "first_transfer_time": None,
                    "last_transfer_time": None,
                }

            edge = aggregated[edge_key]

            # Count every transfer event, even if some fields are missing.
            edge["transfer_count"] += 1

            # Track unique transaction signatures.
            signature = transfer.get("signature")
            if signature:
                edge["signatures"].add(signature)

            # Treat mint=None as native SOL.
            mint = transfer.get("mint")
            mint_key = mint if mint is not None else "native"
            edge["token_mints"].add(mint_key)

            # Sum amounts separately for each token.
            amount = transfer.get("amount")
            if amount is not None:
                try:
                    decimal_amount = Decimal(str(amount))
                    if decimal_amount.is_finite():
                        edge["amount_by_mint"][mint_key] += decimal_amount
                except (InvalidOperation, ValueError):
                    pass

            # Track earliest and latest transfer timestamps.
            event_time = transfer.get("event_time")
            if event_time is not None:
                first_time = edge["first_transfer_time"]
                last_time = edge["last_transfer_time"]

                if first_time is None or event_time < first_time:
                    edge["first_transfer_time"] = event_time

                if last_time is None or event_time > last_time:
                    edge["last_transfer_time"] = event_time

    # Finalize aggregation results into easier-to-consume structures.
    for edge in aggregated.values():
        edge["unique_tx_count"] = len(edge["signatures"])
        edge["signatures"] = sorted(edge["signatures"])
        edge["token_mints"] = sorted(edge["token_mints"])
        edge["amount_by_mint"] = dict(edge["amount_by_mint"])

    return aggregated