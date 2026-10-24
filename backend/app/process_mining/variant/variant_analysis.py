
import pandas as pd


def analyze_variants(
    df: pd.DataFrame,
    wallet_col: str = "wallet_address",
    action_col: str = "action",
    time_col: str = "event_time",
) -> dict:
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df = df.sort_values(
        [wallet_col, time_col, "signature"]
        if "signature" in df.columns
        else [wallet_col, time_col]
    )

    wallet_variants = []
    unique_variants = {}

    for wallet, group in df.groupby(wallet_col, sort=True):
        sequence = tuple(group[action_col].tolist())

        if sequence not in unique_variants:
            variant_id = f"V{len(unique_variants) + 1}"
            unique_variants[sequence] = {
                "variant_id": variant_id,
                "sequence": list(sequence),
                "wallets": [],
            }

        unique_variants[sequence]["wallets"].append(wallet)

        wallet_variants.append({
            "wallet_address": wallet,
            "variant_id": unique_variants[sequence]["variant_id"],
        })

    variants = list(unique_variants.values())

    for variant in variants:
        variant["wallet_count"] = len(variant["wallets"])

    return {
        "wallet_variants": wallet_variants,
        "variants": variants,
    }
