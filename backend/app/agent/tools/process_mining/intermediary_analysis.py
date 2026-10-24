from collections import Counter
from typing import Any

from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.agent.tools.process_mining.common import get_prepared_events
from app.process_mining.intermediary_analysis.intermediary_analysis import (
    get_intermediary,
)

MAX_DETAIL_WALLETS = 10
MAX_MATCHES_PER_WALLET = 10


def _get_result(context: AnalysisContext) -> dict[str, Any]:
    cache_key = "agent_intermediary_result"

    if cache_key not in context.cache:
        df = get_prepared_events(context)
        context.cache[cache_key] = (
            get_intermediary(df)
            if not df.empty
            else {
                "total_intermediary_wallets": 0,
                "wallets": [],
            }
        )

    return context.cache[cache_key]


def _summarize_patterns(wallets: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    total_matches = 0

    for wallet in wallets:
        matches = wallet.get("patterns", [])
        counts.update({match["pattern"] for match in matches})
        total_matches += len(matches)

    return {
        "pattern_wallet_counts": dict(counts),
        "total_matches": total_matches,
    }


def build_intermediary_tools(context: AnalysisContext):
    @tool
    def get_intermediary_overview() -> dict[str, Any]:
        """Summarize intermediary behavior without wallet addresses."""
        result = _get_result(context)

        return {
            "total_intermediary_wallets": result[
                "total_intermediary_wallets"
            ],
            **_summarize_patterns(result["wallets"]),
        }

    @tool
    def get_intermediary_wallet_details(
        wallet_addresses: list[str],
        max_matches_per_wallet: int = 10,
    ) -> dict[str, Any]:
        """Inspect intermediary patterns for up to 10 specified wallets."""
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

            matches = item["patterns"]
            selected = matches[:max_matches_per_wallet]

            details.append({
                "wallet_address": address,
                "found": True,
                "pattern_types": item["pattern_types"],
                "total_matches": len(matches),
                "returned_matches": len(selected),
                "has_more": len(matches) > len(selected),
                "patterns": selected,
            })

        return {"wallets": details}

    return [
        get_intermediary_overview,
        get_intermediary_wallet_details,
    ]