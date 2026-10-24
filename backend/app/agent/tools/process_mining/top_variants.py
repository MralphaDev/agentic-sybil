
from typing import Any

import pandas as pd
from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.variant.variant_top_analysis import (
    analyze_top_variants,
)
from app.agent.tools.process_mining.sequence_utils import collapse_sequence


def build_top_variants_tools(context: AnalysisContext):
    @tool
    def get_top_variants(top_n: int = 10) -> dict[str, Any]:
        """Get the most frequent wallet behavior variants.

        Each wallet is treated as one case.
        Returns ranked collapsed action sequences, wallet frequencies,
        and percentages. Use this tool to identify common wallet behavior
        patterns.
        """

        if not 1 <= top_n <= 20:
            return {"error": "top_n must be between 1 and 20."}

        cache_key = "agent_top_variants_result"

        if cache_key not in context.cache:
            if not context.events:
                result = {
                    "total_wallets": 0,
                    "unique_variants": 0,
                    "top_variants": [],
                }
            else:
                df = pd.DataFrame(context.events)

                df["action"] = df.apply(
                    lambda row: map_event_action(
                        row.to_dict(),
                        target_token_mint=context.target_token_mint,
                    ),
                    axis=1,
                )

                # Match the existing Process Mining dust filter.
                df = df.loc[
                    ~(
                        df["type"].eq("transfer")
                        & (
                            pd.to_numeric(df["amount"], errors="coerce")
                            < 0.001
                        )
                    )
                ].copy()

                if df.empty:
                    result = {
                        "total_wallets": 0,
                        "unique_variants": 0,
                        "top_variants": [],
                    }
                else:
                    df["case:concept:name"] = df["wallet_address"]
                    df["concept:name"] = df["action"]
                    df["time:timestamp"] = pd.to_datetime(
                        df["event_time"],
                        utc=True,
                    )

                    result = analyze_top_variants(df, top_n=20)

            # Cache the original, uncollapsed analysis result.
            context.cache[cache_key] = result

        result = context.cache[cache_key]

        # Collapse sequences only in the returned output.
        return {
            **result,
            "top_variants": [
                {
                    **variant,
                    "variant": collapse_sequence(variant["variant"]),
                }
                for variant in result["top_variants"][:top_n]
            ],
        }

    return [get_top_variants]
