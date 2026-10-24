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
        Four-hour distribution across the full observed time range.

    Notes:
        - Each wallet contributes only its oldest recorded activity.
        - All timestamps are normalized to UTC.
        - Empty time buckets are materialized between the first and last
          observed activity so the frontend can plot a continuous timeline.
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
    # 4. Build a four-hour distribution across the observed data.
    #    Do not hard-code dates: investigations may cover any period.
    # ---------------------------------------------------------
    four_hour = (
        first_activity.dt.floor("4h")
        .value_counts()
        .sort_index()
    )

    # Materialize empty buckets so the frontend can show elapsed time
    # faithfully rather than connecting only non-empty timestamps.
    if not four_hour.empty:
        full_index = pd.date_range(
            start=four_hour.index.min(),
            end=four_hour.index.max(),
            freq="4h",
            tz="UTC",
        )
        four_hour = four_hour.reindex(full_index, fill_value=0)

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

    four_hour_distribution = series_to_distribution(four_hour)
    # Also expose an explicit list for frontend chart libraries. This avoids
    # relying on object-key handling and keeps the UTC timestamp/count schema clear.
    four_hour_buckets = [
        {"timestamp": timestamp.isoformat(), "count": int(count)}
        for timestamp, count in four_hour.items()
    ]

    result = {
        "wallet_count": wallet_count,
        "four_hour_distribution": four_hour_distribution,
        "four_hour_buckets": four_hour_buckets,
        "four_hour_stats": four_hour_stats,
        "charts": {
            "four_hour": {},
        },
    }

    # Verify that the result can be serialized as JSON.
    json.dumps(result, ensure_ascii=False)

    return result
