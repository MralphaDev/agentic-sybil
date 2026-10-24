from collections import defaultdict
from typing import Any


def extract_wallet_transfers(
    events: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Extract incoming and outgoing transfers for each wallet."""

    wallet_transfers: dict[
        str, dict[str, list[dict[str, Any]]]
    ] = defaultdict(
        lambda: {
            "incoming": [],
            "outgoing": [],
        }
    )

    for event in events:
        if event.get("type") != "transfer":
            continue

        sender = event.get("from_user_address")
        receiver = event.get("to_user_address")

        if not sender or not receiver:
            continue

        transfer = {
            "from_wallet": sender,
            "to_wallet": receiver,
            "signature": event.get("signature"),
            "event_time": event.get("event_time"),
            "amount": event.get("amount"),
            "mint": event.get("mint"),
            "protocol": event.get("protocol"),
        }

        wallet_transfers[receiver]["incoming"].append(transfer)
        wallet_transfers[sender]["outgoing"].append(transfer)

    return dict(wallet_transfers)