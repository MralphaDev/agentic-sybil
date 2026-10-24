from decimal import Decimal, InvalidOperation
from typing import Any


LAMPORTS_PER_SOL = Decimal("1000000000")


def to_ui_amount(
    raw_amount: Any,
    decimals: Any,
) -> Decimal | None:
    """Convert a raw token amount into its UI amount."""
    if raw_amount is None or decimals is None:
        return None

    try:
        amount = Decimal(str(raw_amount))
        scale = int(decimals)

        if not amount.is_finite() or scale < 0:
            return None

        return amount / (Decimal(10) ** scale)

    except (ValueError, TypeError, ArithmeticError, InvalidOperation):
        return None


def lamports_to_sol(raw_amount: Any) -> Decimal | None:
    """Convert lamports into SOL."""
    if raw_amount is None:
        return None

    try:
        amount = Decimal(str(raw_amount))

        if not amount.is_finite():
            return None

        return amount / LAMPORTS_PER_SOL

    except (ValueError, TypeError, ArithmeticError, InvalidOperation):
        return None