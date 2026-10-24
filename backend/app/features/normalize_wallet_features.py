
from datetime import datetime
from math import isfinite
from typing import Any


def normalize_wallet_features(
    wallet_features: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Convert JSON-derived wallet features into Python data types."""

    normalized: dict[str, dict[str, Any]] = {}

    for wallet, feature in wallet_features.items():
        item = feature.copy()

        amount = item.get("first_fund_amount")
        if amount is not None:
            amount = float(amount)

            if not isfinite(amount):
                raise ValueError(
                    f"Invalid first_fund_amount for wallet {wallet}: "
                    f"{amount}"
                )

            item["first_fund_amount"] = amount

        fund_time = item.get("first_fund_time")
        if fund_time is not None:
            if isinstance(fund_time, str):
                fund_time = datetime.fromisoformat(
                    fund_time.replace("Z", "+00:00")
                )
            elif not isinstance(fund_time, datetime):
                raise TypeError(
                    f"Invalid first_fund_time for wallet {wallet}: "
                    f"{type(fund_time).__name__}"
                )

            item["first_fund_time"] = fund_time

        normalized[wallet] = item

    return normalized
