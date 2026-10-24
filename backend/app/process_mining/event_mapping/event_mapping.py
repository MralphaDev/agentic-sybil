


def map_event_action(
    event: dict,
    target_token_mint: str,
) -> str:
    """Map a target-independent database event to a target-specific action."""
    translated_type = event.get("translated_type")
    mint = event.get("mint")

    if translated_type == "receive_token":
        if mint == target_token_mint:
            return "receive_target_token"
        if mint is not None:
            return "receive_non_target_token"
        return "unknown_token_receive"

    if translated_type == "transfer_token":
        if mint == target_token_mint:
            return "transfer_target_token"
        if mint is not None:
            return "transfer_non_target_token"
        return "unknown_token_transfer"

    if translated_type == "swap":
        from_token = event.get("from_token")
        to_token = event.get("to_token")

        if from_token == target_token_mint and to_token == target_token_mint:
            return "swap_target_token"

        if to_token == target_token_mint:
            return "buy"

        if from_token == target_token_mint:
            return "sell"

        if from_token is None or to_token is None:
            return "unknown_swap"

        return "swap"

    if translated_type in ("receive_native", "transfer_native"):
        return translated_type

    return translated_type or "unknown"