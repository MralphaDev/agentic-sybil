from typing import Any

from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.agent.tools.process_mining.common import (
    get_variant_analysis,
    get_prepared_events,
)
from app.agent.tools.process_mining.sequence_utils import collapse_sequence
from app.process_mining.variant.variant_sell_analysis import (
    analyze_variant_sells,
)

MAX_WALLETS_PER_CALL = 10


def _get_variant_sell_result(
    context: AnalysisContext,
) -> dict[str, Any]:
    cache_key = "agent_variant_sell_result"

    if cache_key in context.cache:
        return context.cache[cache_key]

    df = get_prepared_events(context)
    variant_analysis = get_variant_analysis(context)

    if df.empty or not variant_analysis["wallet_variants"]:
        result = {
            "total_variants_with_sell": 0,
            "total_wallets_with_sell": 0,
            "variants": [],
        }
        context.cache[cache_key] = result
        return result

    sequences_by_id = {
        item["variant_id"]: item["sequence"]
        for item in variant_analysis["variants"]
    }

    enriched_wallet_variants = [
        {
            **item,
            "variant": sequences_by_id[item["variant_id"]],
        }
        for item in variant_analysis["wallet_variants"]
    ]

    result = analyze_variant_sells(
        df,
        enriched_wallet_variants,
        wallet_col="wallet_address",
        action_col="action",
    )

    context.cache[cache_key] = result
    return result


def build_variant_sell_tools(context: AnalysisContext):
    @tool
    def get_variant_sell_overview(limit: int = 20) -> dict[str, Any]:
        """Summarize behavior variants containing sell actions.
        Returns collapsed sequences and statistics, without wallet lists.
        """
        if not 1 <= limit <= 20:
            return {"error": "limit must be between 1 and 20."}

        result = _get_variant_sell_result(context)
        variant_analysis = get_variant_analysis(context)
        total_wallets = len(variant_analysis["wallet_variants"])

        variants = []

        for item in result["variants"][:limit]:
            variants.append({
                "variant_id": item["variant_id"],
                "sequence": collapse_sequence(item["variant"] or []),
                "wallet_count": item["wallet_count"],
                "sell_wallet_count": item["sell_wallet_count"],
                "sell_wallet_percentage": round(
                    item["sell_wallet_count"] / item["wallet_count"] * 100,
                    2,
                ) if item["wallet_count"] else 0.0,
            })

        return {
            "total_wallets": total_wallets,
            "total_wallets_with_sell": result["total_wallets_with_sell"],
            "overall_sell_wallet_percentage": round(
                result["total_wallets_with_sell"] / total_wallets * 100,
                2,
            ) if total_wallets else 0.0,
            "total_variants_with_sell": result["total_variants_with_sell"],
            "returned_variants": len(variants),
            "has_more": result["total_variants_with_sell"] > len(variants),
            "variants": variants,
        }

    @tool
    def get_variant_sell_wallets(
        variant_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get wallets that performed a sell within a specific variant.
        Use a variant ID returned by get_variant_sell_overview.
        """
        if not 1 <= limit <= MAX_WALLETS_PER_CALL:
            return {"error": "limit must be between 1 and 10."}

        if offset < 0:
            return {"error": "offset must be non-negative."}

        result = _get_variant_sell_result(context)

        variant = next(
            (
                item for item in result["variants"]
                if item["variant_id"] == variant_id
            ),
            None,
        )

        if variant is None:
            return {
                "error": f"No sell behavior found for variant '{variant_id}'."
            }

        wallets = variant["sell_wallets"]
        selected = wallets[offset:offset + limit]

        return {
            "variant_id": variant_id,
            "sequence": collapse_sequence(variant["variant"] or []),
            "total_sell_wallets": len(wallets),
            "offset": offset,
            "returned_wallets": len(selected),
            "has_more": offset + len(selected) < len(wallets),
            "wallets": selected,
        }

    return [
        get_variant_sell_overview,
        get_variant_sell_wallets,
    ]