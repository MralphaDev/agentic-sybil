
from langchain_core.tools import tool

from app.database.queries import get_top_funders


@tool
def get_top_funders_tool(limit: int = 10) -> dict:
    """Get the wallets that first-funded the largest number of distinct wallets.

    Use this to identify potential funding hubs.
    The limit must be between 1 and 20.
    """
    if not 1 <= limit <= 20:
        return {
            "error": "limit must be between 1 and 20"
        }

    funders = get_top_funders(limit=limit)

    return {
        "count": len(funders),
        "funders": funders,
    }
