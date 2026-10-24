from typing import Any


def extract_wallet_swaps(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract swap events from wallet event records."""

    wallet_swaps: list[dict[str, Any]] = []

    for event in events:
        if event.get("type") != "swap":
            continue

        swap = {
            "signature": event.get("signature"),
            "event_time": event.get("event_time"),
            "wallet_address": event.get("from_user_address"),
            "from_token": event.get("from_token"),
            "from_amount": event.get("from_amount"),
            "to_token": event.get("to_token"),
            "to_amount": event.get("to_amount"),
            "protocol": event.get("protocol"),
            "type": event.get("type"),
        }

        wallet_swaps.append(swap)

    return wallet_swaps