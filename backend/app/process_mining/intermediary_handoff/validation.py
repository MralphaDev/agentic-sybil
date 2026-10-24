
import pandas as pd


def validate_inputs(
    df: pd.DataFrame,
    target_token_mint: str,
    max_gap_minutes: float,
    min_hops: int,
    max_hops: int,
    max_chains: int,
    max_actions_after_receive: int,
) -> None:
    required_columns = {
        "wallet_address",
        "event_time",
        "from_user_address",
        "to_user_address",
        "mint",
        "action",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if not target_token_mint:
        raise ValueError("target_token_mint must not be empty")

    if max_gap_minutes < 0:
        raise ValueError("max_gap_minutes must be >= 0")

    if max_hops < 1:
        raise ValueError("max_hops must be >= 1")

    if min_hops < 1 or min_hops > max_hops:
        raise ValueError("min_hops must be between 1 and max_hops")

    if max_chains < 1:
        raise ValueError("max_chains must be >= 1")

    if max_actions_after_receive < 1:
        raise ValueError("max_actions_after_receive must be >= 1")
