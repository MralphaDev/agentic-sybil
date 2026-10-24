from typing import Any

import pandas as pd

from app.agent.context import AnalysisContext
from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.variant.variant_analysis import analyze_variants


def get_prepared_events(context: AnalysisContext) -> pd.DataFrame:
    """Return cached events with mapped actions and dust transfers filtered."""
    cache_key = "agent_behavior_analysis_events"

    if cache_key in context.cache:
        return context.cache[cache_key]

    if not context.events:
        df = pd.DataFrame()
        context.cache[cache_key] = df
        return df

    df = pd.DataFrame(context.events)

    df["action"] = df.apply(
        lambda row: map_event_action(
            row.to_dict(),
            target_token_mint=context.target_token_mint,
        ),
        axis=1,
    )

    df = df.loc[
        ~(
            df["type"].eq("transfer")
            & (
                pd.to_numeric(df["amount"], errors="coerce")
                < 0.001
            )
        )
    ].copy()

    context.cache[cache_key] = df
    return df


def get_variant_analysis(context: AnalysisContext) -> dict[str, Any]:
    """Return cached wallet-to-variant mappings and raw variant sequences."""
    cache_key = "agent_variant_analysis_result"

    if cache_key in context.cache:
        return context.cache[cache_key]

    df = get_prepared_events(context)

    if df.empty:
        result = {
            "wallet_variants": [],
            "variants": [],
        }
    else:
        result = analyze_variants(
            df,
            wallet_col="wallet_address",
            action_col="action",
            time_col="event_time",
        )

    context.cache[cache_key] = result
    return result