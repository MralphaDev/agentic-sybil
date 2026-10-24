
from typing import Any


def classify_transaction(
    tx_type: str | None,
    parsed_data: dict[str, Any],
    transfers: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Classify a transaction into target-independent event types."""

    incoming_token = transfers["incoming_token"]
    outgoing_token = transfers["outgoing_token"]
    incoming_native = transfers["incoming_native"]
    outgoing_native = transfers["outgoing_native"]

    # Handle swaps first.
    if tx_type == "swap":
        return {
            "translated_type": "swap",
            "direction": None,
            "mint": None,
        }

    # Token transfers.
    if incoming_token:
        return {
            "translated_type": "receive_token",
            "direction": "IN",
            "mint": incoming_token[0].get("mint"),
        }

    if outgoing_token:
        return {
            "translated_type": "transfer_token",
            "direction": "OUT",
            "mint": outgoing_token[0].get("mint"),
        }

    # Native SOL transfers.
    if incoming_native:
        return {
            "translated_type": "receive_native",
            "direction": "IN",
            "mint": None,
        }

    if outgoing_native:
        return {
            "translated_type": "transfer_native",
            "direction": "OUT",
            "mint": None,
        }

    # Preserve the original transaction type if no transfer is found.
    return {
        "translated_type": tx_type or "unknown",
        "direction": None,
        "mint": None,
    }
