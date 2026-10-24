
from collections import Counter

import pandas as pd


def analyze_top_variants(
    df: pd.DataFrame,
    top_n: int = 10,
) -> dict:
    """
    Return the most frequent wallet behavior variants.

    Each wallet is treated as one case.
    Variants are ranked by frequency in descending order.

    Required columns:
        - case:concept:name
        - concept:name
        - time:timestamp
    """
    if df.empty:
        return {
            "total_wallets": 0,
            "unique_variants": 0,
            "top_variants": [],
        }

    data = df.sort_values(
        ["case:concept:name", "time:timestamp"],
        kind="stable",
    )

    wallet_variants = (
        data.groupby("case:concept:name", sort=False)[
            "concept:name"
        ]
        .agg(list)
    )

    variant_counts = Counter(
        tuple(actions)
        for actions in wallet_variants
    )

    total_wallets = len(wallet_variants)
    total_unique_variants = len(variant_counts)

    top_variants = []

    for rank, (variant, frequency) in enumerate(
        variant_counts.most_common(top_n),
        start=1,
    ):
        top_variants.append(
            {
                "rank": rank,
                "variant": list(variant),
                "frequency": frequency,
                "percentage": round(
                    frequency / total_wallets * 100,
                    2,
                ),
            }
        )

    return {
        "total_wallets": total_wallets,
        "unique_variants": total_unique_variants,
        "top_variants": top_variants,
    }
