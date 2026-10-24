import pandas as pd


def filter_dust_transfers(
    df: pd.DataFrame,
    min_amount: float = 0.001,
) -> pd.DataFrame:
    """
    Remove transfer events whose amount is below the dust threshold.

    Non-transfer events are preserved.
    The input DataFrame is not modified.
    Rows with unparseable transfer amounts are preserved.
    """
    if df.empty:
        return df.copy()

    required_columns = {"type", "amount"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns for dust filtering: "
            f"{sorted(missing_columns)}"
        )

    amounts = pd.to_numeric(df["amount"], errors="coerce")

    is_dust_transfer = (
        df["type"].eq("transfer")
        & amounts.lt(min_amount)
    )

    return df.loc[~is_dust_transfer].copy()
