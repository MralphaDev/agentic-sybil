from typing import Any


def get_wallet_transfers(
    parsed: dict[str, Any],
    address: str,
) -> dict[str, list[dict[str, Any]]]:
    """Find all native and token transfers involving the wallet."""

    token_transfers = parsed.get("tokenTransfers") or []
    native_transfers = parsed.get("nativeTransfers") or []

    return {
        "incoming_token": [
            transfer
            for transfer in token_transfers
            if transfer.get("toUserAccount") == address
            and transfer.get("fromUserAccount") != address
        ],
        "outgoing_token": [
            transfer
            for transfer in token_transfers
            if transfer.get("fromUserAccount") == address
            and transfer.get("toUserAccount") != address
        ],
        "incoming_native": [
            transfer
            for transfer in native_transfers
            if transfer.get("toUserAccount") == address
            and transfer.get("fromUserAccount") != address
        ],
        "outgoing_native": [
            transfer
            for transfer in native_transfers
            if transfer.get("fromUserAccount") == address
            and transfer.get("toUserAccount") != address
        ],
    }



def get_transfer_addresses(
    transfers: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Return addresses only when there is exactly one matching transfer."""
    #this is a design choice, if one tx contains multiple transfers , this is ambigious and we cannot find the exact from and to address, so we return None, None

    if len(transfers) != 1:
        return None, None

    transfer = transfers[0]

    return (
        transfer.get("fromUserAccount"),
        transfer.get("toUserAccount"),
    )


def get_single_transfer_amount(
    transfers: list[dict[str, Any]],
) -> tuple[Any, Any]:
    """Return raw amount and decimals only for one unambiguous transfer."""

    if len(transfers) != 1:
        return None, None

    transfer = transfers[0]

    return (
        transfer.get("rawTokenAmount"),
        transfer.get("decimals"),
    )


def get_single_native_amount(
    transfers: list[dict[str, Any]],
) -> Any:
    """Return lamports only for one unambiguous native transfer."""

    if len(transfers) != 1:
        return None

    return transfers[0].get("amount")


def get_target_token_decimals(
    transfers: list[dict[str, Any]],
) -> int | None:
    """Get target-token decimals when the matching records agree."""

    decimals = {
        transfer.get("decimals")
        for transfer in transfers
        if transfer.get("decimals") is not None
    }

    if len(decimals) != 1:
        return None

    try:
        raw_value = next(iter(decimals))
        if raw_value is None:
            return None

        value = int(raw_value)
        return value if value >= 0 else None
    except (ValueError, TypeError):
        return None
    


def get_token_decimals(
    transfers: list[dict[str, Any]],
    mint: str | None,
) -> int | None:
    
    # Token decimals are determined by the mint and should remain consistent
  # across all transfers of the same mint within a transaction.

    """Get decimals for a token mint from Helius transfer records."""
    if not mint:
        return None

    # Wrapped SOL uses 9 decimals.
    if mint == "So11111111111111111111111111111111111111112":
        return 9

    decimals = set()

    for transfer in transfers:
        if transfer.get("mint") != mint:
            continue

        # Helius may provide decimals at the top level.
        value = transfer.get("decimals")

        # Support nested rawTokenAmount when it is a dictionary.
        if value is None:
            raw_amount = transfer.get("rawTokenAmount")
            if isinstance(raw_amount, dict):
                value = raw_amount.get("decimals")

        if value is not None:
            try:
                decimals.add(int(value))
            except (TypeError, ValueError):
                continue

    if len(decimals) != 1:
        return None

    result = next(iter(decimals))
    return result if result >= 0 else None

