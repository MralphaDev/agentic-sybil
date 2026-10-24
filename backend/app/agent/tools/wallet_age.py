from typing import Any

import pandas as pd

from app.agent.context import AnalysisContext
from app.process_mining.wallet_age_distribution.first_activity_concentration import (
    analyze_first_activity_concentration,
)


def analyze_four_hour_wallet_age(context: AnalysisContext) -> dict[str, Any]:
    """Return only mint-relative wallet-age evidence, never the full history."""
    df = pd.DataFrame(context.events)
    result = analyze_first_activity_concentration(
        df,
        token_mint_date=context.token_mint_date,
        days_before_mint=10,
        days_after_mint=10,
    )

    # Hard bound the LLM payload even if the underlying analysis changes later.
    buckets = result.get("four_hour_buckets", [])
    if not isinstance(buckets, list):
        buckets = []
    buckets = buckets[:121]

    return {
        "token_mint_date": context.token_mint_date,
        "window": result.get("window", {}),
        "wallet_count": result.get("wallet_count", 0),
        "four_hour_stats": result.get("four_hour_stats", {}),
        "four_hour_buckets": buckets,
        "note": (
            "The timeline is limited to 10 days before through 10 days after "
            "the token mint date. Full historical distribution is intentionally omitted."
        ),
    }
