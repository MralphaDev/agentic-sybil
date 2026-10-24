
from langchain_core.tools import tool

from app.database.queries import get_wallet_profiles


@tool
def get_wallet_info(wallet_addresses: list[str]) -> dict:
    """Retrieve basic profile information for one or more wallets.

    Accepts between 1 and 10 wallet addresses.
    Returns available wallet profile fields and identifies addresses
    that were not found in the database.
    """
    if not 1 <= len(wallet_addresses) <= 10:
        return {
            "error": "Provide between 1 and 10 wallet addresses."
        }

    # Remove duplicate addresses while preserving order.
    wallet_addresses = list(dict.fromkeys(wallet_addresses))

    profiles = get_wallet_profiles(wallet_addresses)
    profiles_by_address = {
        profile["wallet_address"]: profile
        for profile in profiles
    }

    return {
        "wallet_count": len(wallet_addresses),
        "found_count": len(profiles),
        "not_found": [
            address
            for address in wallet_addresses
            if address not in profiles_by_address
        ],
        "wallets": [
            profiles_by_address[address]
            for address in wallet_addresses
            if address in profiles_by_address
        ],
    }
