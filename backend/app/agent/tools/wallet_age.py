from typing import Any

import pandas as pd

from app.agent.context import AnalysisContext
from app.process_mining.wallet_age_distribution.first_activity_concentration import (
    analyze_first_activity_concentration,
)

MAX_ANOMALOUS_BUCKETS = 5
MIN_ANOMALOUS_WALLET_COUNT = 5
ANOMALY_MEAN_MULTIPLIER = 2.0
ROBUST_Z_THRESHOLD = 3.5


def _select_anomalous_buckets(buckets: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep only a handful of clearly elevated 4-hour buckets for the LLM."""
    if not isinstance(buckets, list):
        return [], {"threshold": None, "candidate_count": 0}

    normalized: list[dict[str, Any]] = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        try:
            count = int(bucket.get("count", 0))
        except (TypeError, ValueError):
            continue
        normalized.append({**bucket, "count": count})

    if not normalized:
        return [], {"threshold": None, "candidate_count": 0}

    counts = pd.Series([bucket["count"] for bucket in normalized], dtype="float64")
    median = float(counts.median())
    mad = float((counts - median).abs().median())
    robust_sigma = 1.4826 * mad
    robust_threshold = median + ROBUST_Z_THRESHOLD * robust_sigma
    mean_threshold = float(counts.mean()) * ANOMALY_MEAN_MULTIPLIER
    threshold = max(
        float(MIN_ANOMALOUS_WALLET_COUNT),
        robust_threshold,
        mean_threshold,
    )

    candidates = [
        bucket for bucket in normalized
        if bucket["count"] >= threshold
    ]
    candidates.sort(key=lambda bucket: bucket["count"], reverse=True)
    selected = candidates[:MAX_ANOMALOUS_BUCKETS]
    selected.sort(key=lambda bucket: str(bucket.get("timestamp", "")))

    return selected, {
        "threshold": round(threshold, 2),
        "candidate_count": len(candidates),
        "returned_count": len(selected),
        "selection_rule": (
            f"count >= max({MIN_ANOMALOUS_WALLET_COUNT}, "
            f"{ANOMALY_MEAN_MULTIPLIER}x mean, median + "
            f"{ROBUST_Z_THRESHOLD} robust standard deviations); "
            f"maximum {MAX_ANOMALOUS_BUCKETS} buckets"
        ),
    }


def analyze_four_hour_wallet_age(context: AnalysisContext) -> dict[str, Any]:
    """Return only mint-relative anomalous wallet-age buckets, never full history."""
    df = pd.DataFrame(context.events)
    if not context.token_mint_date:
        wallet_count = int(df["wallet_address"].nunique()) if "wallet_address" in df.columns else 0
        return {
            "token_mint_date": None,
            "window": {"days_before_mint": 10, "days_after_mint": 10},
            "wallet_count": wallet_count,
            "four_hour_stats": {},
            "anomalous_four_hour_buckets": [],
            "bucket_selection": {
                "threshold": None,
                "candidate_count": 0,
                "returned_count": 0,
            },
            "note": "Mint date unavailable; historical timeline omitted.",
        }

    result = analyze_first_activity_concentration(
        df,
        token_mint_date=context.token_mint_date,
        days_before_mint=10,
        days_after_mint=10,
    )

    # The full 121-bucket timeline is used locally for statistics only.
    # Only a maximum of five clearly elevated buckets enters the agent prompt.
    buckets, selection = _select_anomalous_buckets(result.get("four_hour_buckets", []))

    return {
        "token_mint_date": context.token_mint_date,
        "window": result.get("window", {}),
        "wallet_count": result.get("wallet_count", 0),
        "four_hour_stats": result.get("four_hour_stats", {}),
        "anomalous_four_hour_buckets": buckets,
        "bucket_selection": selection,
        "note": (
            "Only clearly elevated 4-hour buckets are included, with a maximum of "
            f"{MAX_ANOMALOUS_BUCKETS}. The full historical distribution is omitted. "
            "An elevated bucket indicates temporal concentration, not proof of Sybil activity."
        ),
    }
