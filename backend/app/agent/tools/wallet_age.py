from typing import Any

import pandas as pd

from app.agent.context import AnalysisContext
from app.process_mining.wallet_age_distribution.first_activity_concentration import (
    analyze_first_activity_concentration,
)


def analyze_four_hour_wallet_age(
    context: AnalysisContext,
) -> dict[str, Any]:
    """Analyze wallet first-activity concentration in the 4-hour window."""

    df = pd.DataFrame(context.events)

    result = analyze_first_activity_concentration(df)

    return {
        "wallet_count": result["wallet_count"],
        "four_hour_distribution": result["four_hour_distribution"],
        "four_hour_stats": result["four_hour_stats"],
    }