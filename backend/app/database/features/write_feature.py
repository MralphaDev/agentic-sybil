from typing import Any

from app.database.connection import get_connection


def write_wallet_features(
    wallet_features: dict[str, dict[str, Any]],
) -> int:
    """Insert or update wallet features in wallet_profiles."""

    if not wallet_features:
        return 0

    rows = [
        (
            wallet,
            feature.get("first_fund_time"),
            feature.get("first_fund_amount"),
            feature.get("first_fund_mint"),
            feature.get("first_funder"),
            feature.get("total_tx_count"),
            feature.get("in_degree"),
            feature.get("out_degree"),
        )
        for wallet, feature in wallet_features.items()
    ]

    sql = """
        INSERT INTO public.wallet_profiles (
            wallet_address,
            first_fund_time,
            first_fund_amount,
            first_fund_token,
            first_funder,
            total_tx_count,
            in_degree,
            out_degree,
            processed_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            NOW(), NOW()
        )
        ON CONFLICT (wallet_address)
        DO UPDATE SET
            first_fund_time = EXCLUDED.first_fund_time,
            first_fund_amount = EXCLUDED.first_fund_amount,
            first_fund_token = EXCLUDED.first_fund_token,
            first_funder = EXCLUDED.first_funder,
            total_tx_count = EXCLUDED.total_tx_count,
            in_degree = EXCLUDED.in_degree,
            out_degree = EXCLUDED.out_degree,
            processed_at = NOW(),
            updated_at = NOW();
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)

    return len(rows)
