
from typing import Any

import pandas as pd
from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.variant.variant_analysis import analyze_variants
from app.agent.tools.process_mining.sequence_utils import (
    collapse_sequence,
)

MAX_OVERVIEW_VARIANTS = 50
MAX_WALLETS_PER_CALL = 10


def _get_variant_analysis(context: AnalysisContext) -> dict[str, Any]:
    """Build and cache variant analysis for the current investigation."""

    cache_key = "agent_variant_analysis_result"

    if cache_key in context.cache:
        return context.cache[cache_key]

    empty_result = {
        "wallet_variants": [],
        "variants": [],
    }

    if not context.events:
        context.cache[cache_key] = empty_result
        return empty_result

    df = pd.DataFrame(context.events)

    df["action"] = df.apply(
        lambda row: map_event_action(
            row.to_dict(),
            target_token_mint=context.target_token_mint,
        ),
        axis=1,
    )

    # Keep the same dust-transfer filtering rule as run_process_mining().
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
        context.cache[cache_key] = empty_result
        return empty_result

    result = analyze_variants(
        df,
        wallet_col="wallet_address",
        action_col="action",
        time_col="event_time",
    )

    context.cache[cache_key] = result
    return result


def build_variant_tools(context: AnalysisContext):
    @tool
    def get_variant_overview(
        limit: int = 30,
    ) -> dict[str, Any]:
        """Get an overview of wallet behavior variants.

        Returns variant IDs, action sequences, wallet counts, and percentages.
        Does not return wallet address lists.

        Variants are ranked by wallet count, highest first.
        Use get_variant_wallets to inspect wallets belonging to a variant.

        limit: Number of variants to return, between 1 and 50.
        Variant IDs are only valid within the current analysis context.
        """

        if not 1 <= limit <= MAX_OVERVIEW_VARIANTS:
            return {
                "error": (
                    f"limit must be between 1 and "
                    f"{MAX_OVERVIEW_VARIANTS}."
                )
            }

        result = _get_variant_analysis(context)
        variants = result["variants"]
        total_wallets = len(result["wallet_variants"])

        ranked_variants = sorted(
            variants,
            key=lambda item: (
                -item["wallet_count"],
                item["variant_id"],
            ),
        )

        overview = [
            {
                "variant_id": variant["variant_id"],
                "sequence": collapse_sequence(variant["sequence"]),
                "wallet_count": variant["wallet_count"],
                "percentage": round(
                    variant["wallet_count"] / total_wallets * 100,
                    2,
                ) if total_wallets else 0.0,
            }
            for variant in ranked_variants[:limit]
        ]

        return {
            "total_wallets": total_wallets,
            "total_variants": len(variants),
            "returned_variants": len(overview),
            "has_more": len(variants) > len(overview),
            "variants": overview,
        }

    @tool
    def get_variant_wallets(
        variant_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get wallet addresses belonging to a specific behavior variant.

        Use a variant ID obtained from get_variant_overview.
        Returns at most 10 wallet addresses per call.

        variant_id: Variant identifier such as V7.
        limit: Number of wallet addresses to return, between 1 and 10.
        offset: Number of matching wallets to skip for pagination.
        """

        if not 1 <= limit <= MAX_WALLETS_PER_CALL:
            return {
                "error": (
                    f"limit must be between 1 and "
                    f"{MAX_WALLETS_PER_CALL}."
                )
            }

        if offset < 0:
            return {"error": "offset must be non-negative."}

        result = _get_variant_analysis(context)

        variant = next(
            (
                item
                for item in result["variants"]
                if item["variant_id"] == variant_id
            ),
            None,
        )

        if variant is None:
            return {
                "error": (
                    f"Variant '{variant_id}' was not found "
                    "in the current analysis context."
                )
            }

        wallets = variant["wallets"]
        selected_wallets = wallets[offset:offset + limit]

        return {
            "variant_id": variant_id,
            "sequence": collapse_sequence(variant["sequence"]),
            "total_wallets": len(wallets),
            "offset": offset,
            "returned_wallets": len(selected_wallets),
            "has_more": offset + len(selected_wallets) < len(wallets),
            "wallets": selected_wallets,
        }

    return [
        get_variant_overview,
        get_variant_wallets,
    ]
