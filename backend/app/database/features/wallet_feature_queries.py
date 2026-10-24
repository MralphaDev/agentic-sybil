
from typing import Any

from app.database.connection import get_connection


def get_wallet_features() -> list[dict[str, Any]]:
    """Fetch features for all wallets."""

    sql = """
        SELECT
            wallet_address,
            first_fund_time,
            first_fund_amount,
            first_fund_token,
            first_funder,
            total_tx_count,
            in_degree,
            out_degree
        FROM public.wallet_profiles;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description] # type: ignore
            rows = cur.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]


def get_wallet_feature(
    wallet_address: str,
) -> dict[str, Any] | None:
    """Fetch features for a single wallet."""

    sql = """
        SELECT
            wallet_address,
            first_fund_time,
            first_fund_amount,
            first_fund_token,
            first_funder,
            total_tx_count,
            in_degree,
            out_degree
        FROM public.wallet_profiles
        WHERE wallet_address = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (wallet_address,))
            row = cur.fetchone()

            if row is None:
                return None

            columns = [desc[0] for desc in cur.description] # type: ignore

    return dict(zip(columns, row))
