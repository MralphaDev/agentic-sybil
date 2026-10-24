from pathlib import Path
from typing import Any

import json

import matplotlib.pyplot as plt
import pandas as pd


def analyze_first_activity_concentration(
    df: pd.DataFrame,
    output_dir: str | Path = ".",
) -> dict[str, Any]:
    """
    Analyze the distribution of each wallet's oldest recorded activity.

    Analysis:
        Four-hour distribution from 2025-09-01 to 2025-10-10 inclusive.

    Notes:
        - Each wallet contributes only its oldest recorded activity.
        - All timestamps are normalized to UTC.
        - Date filtering happens AFTER finding each wallet's
          oldest activity in the full input dataset.
        - Empty time buckets are not materialized.
        - Returned statistics are JSON-compatible.
    """

    # ---------------------------------------------------------
    # 1. Validate input
    # ---------------------------------------------------------
    required_columns = {"wallet_address", "event_time"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if df.empty:
        return {
            "wallet_count": 0,
            "four_hour_distribution": {},
            "four_hour_stats": {},
            "charts": {},
        }

    # ---------------------------------------------------------
    # 2. Clean timestamps and wallet addresses
    # ---------------------------------------------------------
    data = df[["wallet_address", "event_time"]].copy()

    data = data.dropna(
        subset=["wallet_address", "event_time"]
    )

    data["wallet_address"] = (
        data["wallet_address"].astype(str).str.strip()
    )

    data = data[data["wallet_address"] != ""]

    data["event_time"] = pd.to_datetime(
        data["event_time"],
        utc=True,
        errors="coerce",
    )

    data = data.dropna(subset=["event_time"])

    if data.empty:
        return {
            "wallet_count": 0,
            "four_hour_distribution": {},
            "four_hour_stats": {},
            "charts": {},
        }

    # ---------------------------------------------------------
    # 3. Find each wallet's oldest activity FIRST
    # ---------------------------------------------------------
    first_activity = (
        data.groupby("wallet_address")["event_time"]
        .min()
        .sort_values()
    )

    wallet_count = int(len(first_activity))

    # ---------------------------------------------------------
    # 4. Define the four-hour analysis window
    # ---------------------------------------------------------
    four_hour_start = pd.Timestamp(
        "2025-09-01 00:00:00", tz="UTC"
    )

    four_hour_end = pd.Timestamp(
        "2025-10-11 00:00:00", tz="UTC"
    )

    # ---------------------------------------------------------
    # 5. Calculate four-hour distribution
    # ---------------------------------------------------------
    four_hour_data = first_activity[
        (first_activity >= four_hour_start)
        & (first_activity < four_hour_end)
    ]

    four_hour = (
        four_hour_data.dt.floor("4h")
        .value_counts()
        .sort_index()
    )

    # ---------------------------------------------------------
    # 6. Calculate distribution statistics
    # ---------------------------------------------------------
    def distribution_stats(
        counts: pd.Series,
        total_wallets: int,
    ) -> dict[str, Any]:
        if counts.empty:
            return {
                "wallets_in_window": 0,
                "total_wallets": total_wallets,
                "share_of_all_wallets": 0.0,
                "nonempty_buckets": 0,
                "peak_bucket": None,
                "peak_count": 0,
                "peak_share_within_window": 0.0,
                "mean_wallets_per_nonempty_bucket": 0.0,
            }

        window_wallets = int(counts.sum())
        peak_count = int(counts.max())
        peak_bucket = counts.idxmax()

        return {
            "wallets_in_window": window_wallets,
            "total_wallets": total_wallets,
            "share_of_all_wallets": round(
                window_wallets / total_wallets, 6
            ) if total_wallets else 0.0,
            "nonempty_buckets": int(len(counts)),
            "peak_bucket": peak_bucket.isoformat(),  # type: ignore
            "peak_count": peak_count,
            "peak_share_within_window": round(
                peak_count / window_wallets, 6
            ) if window_wallets else 0.0,
            "mean_wallets_per_nonempty_bucket": round(
                float(counts.mean()), 4
            ),
        }

    four_hour_stats = distribution_stats(
        four_hour,
        wallet_count,
    )

    # ---------------------------------------------------------
    # 7. Plotting helper
    # ---------------------------------------------------------
    def plot_distribution(
        counts: pd.Series,
        title: str,
        xlabel: str,
        filename: str,
        tick_count: int = 10,
    ) -> str:
        chart_path = output_path / filename

        fig, ax = plt.subplots(figsize=(14, 6))

        if counts.empty:
            ax.text(
                0.5,
                0.5,
                "No wallet first activities in this time window",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

            ax.set_xticks([])
            ax.set_yticks([])

        else:
            ax.bar(
                counts.index,
                counts.values,  # type: ignore
                width=0.8,
                align="center",
            )

            ax.set_ylabel("Number of wallets")
            ax.set_xlabel(xlabel)

            # Display a manageable number of date labels.
            if len(counts) > tick_count:
                positions = list(
                    range(
                        0,
                        len(counts),
                        max(1, len(counts) // tick_count),
                    )
                )

                if positions[-1] != len(counts) - 1:
                    positions.append(len(counts) - 1)

                ax.set_xticks(
                    [counts.index[i] for i in positions]
                )

            fig.autofmt_xdate(rotation=45)

        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)

        fig.tight_layout()
        fig.savefig(
            chart_path,
            dpi=160,
            bbox_inches="tight",
        )
        plt.close(fig)

        return str(chart_path)

    # ---------------------------------------------------------
    # 8. Generate the four-hour chart
    # ---------------------------------------------------------
    '''four_hour_chart = plot_distribution(
        counts=four_hour,
        title=(
            "Wallet First Activity Distribution "
            "(4-Hour Buckets, Sep 1 - Oct 10, 2025)"
        ),
        xlabel="Time (UTC)",
        filename="first_activity_4h.png",
    )'''

    # ---------------------------------------------------------
    # 9. Convert distribution to a JSON-compatible dictionary
    # ---------------------------------------------------------
    def series_to_distribution(
        counts: pd.Series,
    ) -> dict[str, int]:
        return {
            timestamp.isoformat(): int(count)  # type: ignore
            for timestamp, count in counts.items()
        }

    result = {
        "wallet_count": wallet_count,
        "four_hour_distribution": series_to_distribution(
            four_hour
        ),
        "four_hour_stats": four_hour_stats,
        "charts": {
            "four_hour": {},
        },
    }

    # Verify that the result can be serialized as JSON.
    json.dumps(result, ensure_ascii=False)

    return result
