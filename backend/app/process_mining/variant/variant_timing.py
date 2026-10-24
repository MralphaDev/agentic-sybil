
import pandas as pd


def analyze_variant_timing(
    df: pd.DataFrame,
    wallet_variants: list[dict],
    wallet_col: str = "wallet_address",
    action_col: str = "action",
    time_col: str = "event_time",
    top_n: int = 15,
) -> list[dict]:
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)

    df = df.sort_values(
        [wallet_col, time_col, "signature"]
        if "signature" in df.columns
        else [wallet_col, time_col]
    )

    wallet_to_variant = {
        item["wallet_address"]: item["variant_id"]
        for item in wallet_variants
    }

    df["variant_id"] = df[wallet_col].map(wallet_to_variant)

    df["previous_action"] = (
        df.groupby(wallet_col)[action_col].shift(1)
    )

    # Calculate time intervals in minutes.
    df["time_delta_minutes"] = (
        df.groupby(wallet_col)[time_col]
        .diff()
        .dt.total_seconds()
        / 60
    )

    # Each row represents the transition into the current action.
    intervals = df.dropna(
        subset=["time_delta_minutes", "previous_action"]
    ).copy()

    intervals["from_action"] = intervals["previous_action"]
    intervals["to_action"] = intervals[action_col]

    results = []

    for variant_id, group in df.groupby("variant_id", sort=False):
        variant_intervals = intervals[
            intervals["variant_id"] == variant_id
        ]

        deltas = variant_intervals["time_delta_minutes"]

        transitions = []

        for (source, target), edge_group in (
            variant_intervals.groupby(
                ["from_action", "to_action"]
            )
        ):
            values = edge_group["time_delta_minutes"]

            transitions.append({
                "from": source,
                "to": target,
                "interval_count": int(values.count()),
                "median_minutes": round(
                    float(values.median()), 2
                ),
                "mean_minutes": round(
                    float(values.mean()), 2
                ),
            })

        results.append({
            "variant_id": variant_id,
            "wallet_count": int(group[wallet_col].nunique()),
            "interval_count": int(deltas.count()),
            "median_minutes": (
                round(float(deltas.median()), 2)
                if not deltas.empty else None
            ),
            "mean_minutes": (
                round(float(deltas.mean()), 2)
                if not deltas.empty else None
            ),
            "transitions": transitions,
        })

    # Rank variants by median time, shortest first.
    # Variants without valid intervals are placed last.
    results.sort(
        key=lambda item: (
            item["median_minutes"] is None,
            item["median_minutes"]
            if item["median_minutes"] is not None
            else float("inf"),
        )
    )

    return results[:top_n]
