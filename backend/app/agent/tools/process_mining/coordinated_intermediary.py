from collections import Counter
from typing import Any

from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.agent.tools.process_mining.common import get_prepared_events
from app.process_mining.intermediary_analysis.coordinated_intermediary_analysis import (
    get_coordinated_intermediary,
)

MAX_DETAIL_WALLETS = 10
MAX_MATCHES_PER_WALLET = 10
DEFAULT_MAX_GAP_MINUTES = 5


def _get_result(context: AnalysisContext) -> dict[str, Any]:
    cache_key = "agent_coordinated_intermediary_result"

    if cache_key not in context.cache:
        df = get_prepared_events(context)
        context.cache[cache_key] = (
            get_coordinated_intermediary(
                df,
                max_gap_minutes=DEFAULT_MAX_GAP_MINUTES,
            )
            if not df.empty
            else {
                "max_gap_minutes": DEFAULT_MAX_GAP_MINUTES,
                "total_coordinated_wallets": 0,
                "wallets": [],
            }
        )

    return context.cache[cache_key]


def _summarize_patterns(wallets: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    total_matches = 0

    for wallet in wallets:
        matches = wallet.get("matched_pairs", [])
        counts.update({match["pattern"] for match in matches})
        total_matches += len(matches)

    return {
        "pattern_wallet_counts": dict(counts),
        "total_matches": total_matches,
    }


def build_coordinated_intermediary_tools(context: AnalysisContext):
    @tool
    def get_coordinated_intermediary_overview() -> dict[str, Any]:
        """Summarize coordinated intermediary behavior within five minutes."""
        result = _get_result(context)
        wallets = result["wallets"]

        gap_values = [
            match["gap_seconds"]
            for wallet in wallets
            for match in wallet["matched_pairs"]
        ]

        return {
            "max_gap_minutes": result["max_gap_minutes"],
            "total_coordinated_wallets": result[
                "total_coordinated_wallets"
            ],
            **_summarize_patterns(wallets),
            "min_gap_seconds": min(gap_values) if gap_values else None,
            "max_gap_seconds": max(gap_values) if gap_values else None,
        }

    @tool
    def get_coordinated_intermediary_wallet_details(
        wallet_addresses: list[str],
        max_matches_per_wallet: int = 10,
    ) -> dict[str, Any]:
        """Inspect coordinated intermediary matches for up to 10 wallets."""
        if not 1 <= len(wallet_addresses) <= MAX_DETAIL_WALLETS:
            return {"error": "Provide between 1 and 10 wallet addresses."}

        if not 1 <= max_matches_per_wallet <= MAX_MATCHES_PER_WALLET:
            return {"error": "max_matches_per_wallet must be between 1 and 10."}

        result = _get_result(context)
        by_wallet = {
            item["wallet_address"]: item
            for item in result["wallets"]
        }

        details = []

        for address in dict.fromkeys(wallet_addresses):
            item = by_wallet.get(address)

            if item is None:
                details.append({
                    "wallet_address": address,
                    "found": False,
                })
                continue

            matches = item["matched_pairs"]
            selected = matches[:max_matches_per_wallet]

            details.append({
                "wallet_address": address,
                "found": True,
                "pattern_types": item["pattern_types"],
                "total_matches": item["matched_pair_count"],
                "returned_matches": len(selected),
                "has_more": len(matches) > len(selected),
                "matched_pairs": selected,
            })

        return {"wallets": details}

    return [
        get_coordinated_intermediary_overview,
        get_coordinated_intermediary_wallet_details,
    ]