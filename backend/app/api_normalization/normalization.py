
from typing import Any

from app.api_normalization.token_amount import (
    lamports_to_sol,
    to_ui_amount,
)
from app.api_normalization.transfer_details import (
    get_single_native_amount,
    get_single_transfer_amount,
    get_transfer_addresses,
    get_wallet_transfers,
    get_token_decimals,
)
from app.api_normalization.transaction_classification import (
    classify_transaction,
)


def normalize_transaction(
    item: dict[str, Any],
    address: str,
) -> dict[str, Any] | None:
    """Normalize one Helius transaction into target-independent events."""

    parsed = item.get("parsed") or {}
    summary = parsed.get("summary") or {}
    parsed_data = summary.get("parsedData") or {}

    signature = item.get("signature")
    if not signature:
        return None

    tx_type = parsed_data.get("type") or summary.get("type")
    kind = parsed_data.get("kind")
    protocol = parsed_data.get("protocol")

    transfers = get_wallet_transfers(
        parsed=parsed,
        address=address,
    )

    classification = classify_transaction(
        tx_type=tx_type,
        parsed_data=parsed_data,
        transfers=transfers,
    )

    translated_type = classification["translated_type"]
    direction = classification["direction"]
    mint = classification["mint"]

    # Select transfers based on the global event classification.
    if translated_type == "receive_token":
        selected_transfers = transfers["incoming_token"]
    elif translated_type == "transfer_token":
        selected_transfers = transfers["outgoing_token"]
    elif translated_type == "receive_native":
        selected_transfers = transfers["incoming_native"]
    elif translated_type == "transfer_native":
        selected_transfers = transfers["outgoing_native"]
    elif translated_type == "swap":
        selected_transfers = (
            transfers["outgoing_token"]
            or transfers["incoming_token"]
        )
    else:
        selected_transfers = []

    from_user_address, to_user_address = get_transfer_addresses(
        selected_transfers
    )

    amount = None
    swap_from_amount = None
    swap_to_amount = None

    if translated_type == "swap":
        all_token_transfers = parsed.get("tokenTransfers") or []

        swap_from_amount = to_ui_amount(
            parsed_data.get("in_amount"),
            get_token_decimals(
                all_token_transfers,
                parsed_data.get("input_mint"),
            ),
        )

        swap_to_amount = to_ui_amount(
            parsed_data.get("actual_out_amount"),
            get_token_decimals(
                all_token_transfers,
                parsed_data.get("output_mint"),
            ),
        )

    elif translated_type in ("receive_token", "transfer_token"):
        raw_amount, decimals = get_single_transfer_amount(
            selected_transfers
        )
        amount = to_ui_amount(raw_amount, decimals)

    elif translated_type in ("receive_native", "transfer_native"):
        raw_amount = get_single_native_amount(selected_transfers)
        amount = lamports_to_sol(raw_amount)

    result = {
        "signature": signature,
        "type": tx_type,
        "translated_type": translated_type,
        "time": parsed.get("blockTime"),
        "from_user_address": from_user_address,
        "to_user_address": to_user_address,
    }

    if translated_type == "swap":
        result.update({
            "kind": kind,
            "from_token": parsed_data.get("input_mint"),
            "from_amount": swap_from_amount,
            "to_token": parsed_data.get("output_mint"),
            "to_amount": swap_to_amount,
            "protocol": protocol,
        })
    else:
        result.update({
            "direction": direction,
            "amount": amount,
            "mint": mint,
        })

    return result
