
import pandas as pd


def analyze_variant_sells(
    df: pd.DataFrame,
    wallet_variants: list[dict],
    wallet_col: str = "wallet_address",
    action_col: str = "action",
) -> dict:
    """
    Identify variants containing sell and list the wallets
    associated with each variant that performed sell.
    """

    if df.empty or not wallet_variants:
        return {
            "total_variants_with_sell": 0,
            "total_wallets_with_sell": 0,
            "variants": [],
        }

    wallet_to_variant = {
        item["wallet_address"]: item["variant_id"]
        for item in wallet_variants
    }

    data = df.copy()
    data["variant_id"] = data[wallet_col].map(wallet_to_variant)

    # Wallets that performed at least one sell.
    sell_wallets = set(
        data.loc[
            data[action_col].eq("sell"),
            wallet_col,
        ].dropna()
    )

    # Count all wallets and sell wallets for each variant.
    results = []

    for variant_id, group in data.groupby(
        "variant_id",
        sort=False,
        dropna=True,
    ):
        wallets = sorted(
            group[wallet_col].dropna().unique().tolist()
        )

        wallets_with_sell = sorted(
            set(wallets) & sell_wallets
        )

        if not wallets_with_sell:
            continue

        # Recover the variant sequence.
        variant_info = next(
            (
                item for item in wallet_variants
                if item["variant_id"] == variant_id
            ),
            {},
        )

        results.append({
            "variant_id": variant_id,
            "variant": variant_info.get("variant"),
            "wallet_count": len(wallets),
            "sell_wallet_count": len(wallets_with_sell),
            "sell_wallets": wallets_with_sell,
        })

    # Variants with the most sell wallets first.
    results.sort(
        key=lambda item: (
            item["sell_wallet_count"],
            item["wallet_count"],
        ),
        reverse=True,
    )

    return {
        "total_variants_with_sell": len(results),
        "total_wallets_with_sell": len(sell_wallets),
        "variants": results,
    }
