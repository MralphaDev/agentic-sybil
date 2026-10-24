
import pandas as pd


def analyze_intermediary_support(
    df: pd.DataFrame,
    intermediary_wallets: set[str],
) -> dict:
    """Analyze distinct counterparties of identified intermediary wallets."""

    required = {"from_user_address", "to_user_address"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    results = []

    for wallet in sorted(intermediary_wallets):
        incoming = set(
            df.loc[df["to_user_address"].eq(wallet), "from_user_address"]
            .dropna()
        ) - {wallet}

        outgoing = set(
            df.loc[df["from_user_address"].eq(wallet), "to_user_address"]
            .dropna()
        ) - {wallet}

        results.append({
            "wallet_address": wallet,
            "incoming_counterparty_count": len(incoming),
            "outgoing_counterparty_count": len(outgoing),
            "distinct_counterparty_count": len(incoming | outgoing),
            "incoming_counterparties": sorted(incoming),
            "outgoing_counterparties": sorted(outgoing),
        })

    results.sort(
        key=lambda item: item["distinct_counterparty_count"],
        reverse=True,
    )

    return {
        "total_intermediary_wallets": len(intermediary_wallets),
        "wallets": results,
    }


def analyze_seller_behavior(
    df: pd.DataFrame,
    seller_wallets: set[str],
) -> dict:
    """Analyze sell frequency and intervals for identified seller wallets."""

    results = []

    for wallet in sorted(seller_wallets):
        timestamps = (
            df.loc[
                df["wallet_address"].eq(wallet)
                & df["action"].eq("sell"),
                "time:timestamp",
            ]
            .dropna()
            .sort_values()
        )

        gaps = timestamps.diff().dt.total_seconds().dropna()

        mean_gap = float(gaps.mean()) if not gaps.empty else None
        median_gap = float(gaps.median()) if not gaps.empty else None
        std_gap = (
            float(gaps.std())
            if len(gaps) >= 2
            else None
        )

        results.append({
            "wallet_address": wallet,
            "sell_count": len(timestamps),
            "repeated_seller": len(timestamps) >= 2,
            "mean_sell_interval_seconds": mean_gap,
            "median_sell_interval_seconds": median_gap,
            "sell_interval_std_seconds": std_gap,
            "sell_interval_cv": (
                std_gap / mean_gap
                if std_gap is not None
                and mean_gap is not None
                and mean_gap > 0
                else None
            ),
        })

    results.sort(
        key=lambda item: item["sell_count"],
        reverse=True,
    )

    return {
        "identified_seller_count": len(seller_wallets),
        "active_seller_count": sum(
            item["sell_count"] > 0 for item in results
        ),
        "repeated_seller_count": sum(
            item["repeated_seller"] for item in results
        ),
        "total_sell_events": sum(
            item["sell_count"] for item in results
        ),
        "sellers": results,
    }
