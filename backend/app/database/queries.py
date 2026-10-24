
from app.database.connection import get_connection


def save_wallet_event(wallet_address: str, result: dict) -> None:
    sql = """
        INSERT INTO public.wallet_event_log (
            wallet_address,
            signature,
            type,
            translated_type,
            event_time,
            from_user_address,
            to_user_address,
            kind,
            from_token,
            from_amount,
            to_token,
            to_amount,
            protocol,
            direction,
            amount,
            mint
        )
        VALUES (
            %(wallet_address)s,
            %(signature)s,
            %(type)s,
            %(translated_type)s,
            to_timestamp(%(event_time)s),
            %(from_user_address)s,
            %(to_user_address)s,
            %(kind)s,
            %(from_token)s,
            %(from_amount)s,
            %(to_token)s,
            %(to_amount)s,
            %(protocol)s,
            %(direction)s,
            %(amount)s,
            %(mint)s
        )
        ON CONFLICT (wallet_address, signature)
        DO UPDATE SET
            type = EXCLUDED.type,
            translated_type = EXCLUDED.translated_type,
            event_time = EXCLUDED.event_time,
            from_user_address = EXCLUDED.from_user_address,
            to_user_address = EXCLUDED.to_user_address,
            kind = EXCLUDED.kind,
            from_token = EXCLUDED.from_token,
            from_amount = EXCLUDED.from_amount,
            to_token = EXCLUDED.to_token,
            to_amount = EXCLUDED.to_amount,
            protocol = EXCLUDED.protocol,
            direction = EXCLUDED.direction,
            amount = EXCLUDED.amount,
            mint = EXCLUDED.mint;
    """

    params = {
        "wallet_address": wallet_address,
        "signature": result["signature"],
        "type": result.get("type"),
        "translated_type": result["translated_type"],
        "event_time": result.get("time"),
        "from_user_address": result.get("from_user_address"),
        "to_user_address": result.get("to_user_address"),
        "kind": result.get("kind"),
        "from_token": result.get("from_token"),
        "from_amount": result.get("from_amount"),
        "to_token": result.get("to_token"),
        "to_amount": result.get("to_amount"),
        "protocol": result.get("protocol"),
        "direction": result.get("direction"),
        "amount": result.get("amount"),
        "mint": result.get("mint"),
    }

    with get_connection() as conn:
        conn.execute(sql, params)


def save_wallet_holdings(
    wallet_address: str,
    holdings: list[dict],
) -> None:
    """Replace a wallet's current token holdings snapshot."""

    delete_sql = """
        DELETE FROM public.wallet_token_holdings
        WHERE wallet_address = %s;
    """

    insert_sql = """
        INSERT INTO public.wallet_token_holdings (
            wallet_address,
            mint,
            amount,
            decimals,
            program,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, now());
    """

    with get_connection() as conn:
        conn.execute(delete_sql, (wallet_address,))

        if holdings:
            with conn.cursor() as cur:
                cur.executemany(
                    insert_sql,
                    [
                        (
                            wallet_address,
                            holding["mint"],
                            holding["amount"],
                            holding["decimals"],
                            holding.get("program"),
                        )
                        for holding in holdings
                    ],
                )
                

def get_wallet_profile(wallet_address: str) -> dict | None:
    """Return a wallet profile, or None if the wallet does not exist."""

    sql = """
        SELECT *
        FROM public.wallet_profiles
        WHERE wallet_address = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (wallet_address,))
            row = cur.fetchone()

            if row is None:
                return None

            columns = [column.name for column in (cur.description or [])]
            return dict(zip(columns, row))


def upsert_wallet_profile(
    wallet_address: str,
    is_contract: bool,
    is_exchange: bool,
    forensic_status: str,
    first_active_time=None,
    first_fund_time=None,
    first_fund_amount=None,
    first_fund_token=None,
    total_tx_count=None,
    processed_at=None,
) -> None:
    """Insert or update a wallet profile."""

    sql = """
        INSERT INTO public.wallet_profiles (
            wallet_address,
            is_contract,
            is_exchange,
            forensic_status,
            first_active_time,
            first_fund_time,
            first_fund_amount,
            first_fund_token,
            total_tx_count,
            processed_at,
            updated_at
        )
        VALUES (
            %(wallet_address)s,
            %(is_contract)s,
            %(is_exchange)s,
            %(forensic_status)s,
            %(first_active_time)s,
            %(first_fund_time)s,
            %(first_fund_amount)s,
            %(first_fund_token)s,
            %(total_tx_count)s,
            %(processed_at)s,
            now()
        )
        ON CONFLICT (wallet_address)
        DO UPDATE SET
            is_contract = EXCLUDED.is_contract,
            is_exchange = EXCLUDED.is_exchange,
            forensic_status = EXCLUDED.forensic_status,
            first_active_time = COALESCE(
                EXCLUDED.first_active_time,
                wallet_profiles.first_active_time
            ),
            first_fund_time = COALESCE(
                EXCLUDED.first_fund_time,
                wallet_profiles.first_fund_time
            ),
            first_fund_amount = COALESCE(
                EXCLUDED.first_fund_amount,
                wallet_profiles.first_fund_amount
            ),
            first_fund_token = COALESCE(
                EXCLUDED.first_fund_token,
                wallet_profiles.first_fund_token
            ),
            total_tx_count = COALESCE(
                EXCLUDED.total_tx_count,
                wallet_profiles.total_tx_count
            ),
            processed_at = COALESCE(
                EXCLUDED.processed_at,
                wallet_profiles.processed_at
            ),
            updated_at = now();
    """

    params = {
        "wallet_address": wallet_address,
        "is_contract": is_contract,
        "is_exchange": is_exchange,
        "forensic_status": forensic_status,
        "first_active_time": first_active_time,
        "first_fund_time": first_fund_time,
        "first_fund_amount": first_fund_amount,
        "first_fund_token": first_fund_token,
        "total_tx_count": total_tx_count,
        "processed_at": processed_at,
    }

    with get_connection() as conn:
        conn.execute(sql, params)


def get_wallet_events() -> list[dict]:
    """Fetch all wallet events for Process Mining."""

    sql = """
        SELECT
            wallet_address,
            signature,
            type,
            translated_type,
            event_time,
            from_user_address,
            to_user_address,
            kind,
            from_token,
            from_amount,
            to_token,
            to_amount,
            protocol,
            direction,
            amount,
            mint
        FROM public.wallet_event_log
        ORDER BY event_time ASC NULLS LAST, signature ASC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

            columns = [column.name for column in cur.description] # type: ignore

            return [
                dict(zip(columns, row))
                for row in rows
            ]
            
def get_wallet_events_enriched() -> list[dict]:
    """Wallet events joined with wallet_profiles for the wallet itself,
    the sender (from_user_address) and the receiver (to_user_address)."""

    sql = """
        SELECT
            e.wallet_address,
            e.signature,
            e.type,
            e.translated_type,
            e.event_time,
            e.from_user_address,
            e.to_user_address,
            e.kind,
            e.from_token,
            e.from_amount,
            e.to_token,
            e.to_amount,
            e.protocol,
            e.direction,
            e.amount,
            e.mint,

            p.is_contract      AS self_is_contract,
            p.is_exchange      AS self_is_exchange,
            p.first_fund_time,
            p.first_fund_amount,
            p.first_fund_token,
            p.total_tx_count,

            fp.is_exchange     AS from_is_exchange,
            fp.is_contract     AS from_is_contract,
            tp.is_exchange     AS to_is_exchange,
            tp.is_contract     AS to_is_contract
        FROM public.wallet_event_log e
        LEFT JOIN public.wallet_profiles p
               ON p.wallet_address  = e.wallet_address
        LEFT JOIN public.wallet_profiles fp
               ON fp.wallet_address = e.from_user_address
        LEFT JOIN public.wallet_profiles tp
               ON tp.wallet_address = e.to_user_address
        ORDER BY e.event_time ASC NULLS LAST, e.signature ASC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [c.name for c in cur.description]  # type: ignore
            return [dict(zip(columns, row)) for row in rows]

def get_wallet_profile_addresses() -> set[str]:
    """Return all wallet addresses stored in wallet_profiles."""

    query = """
        SELECT wallet_address
        FROM public.wallet_profiles
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return {row[0] for row in rows if row[0]}



def get_top_funders(limit: int = 10) -> list[dict]:
    """Return wallets ranked by the number of distinct wallets they first funded."""

    sql = """
        SELECT
            first_funder AS wallet_address,
            COUNT(DISTINCT wallet_address) AS funded_wallet_count
        FROM public.wallet_profiles
        WHERE first_funder IS NOT NULL
          AND first_funder <> ''
        GROUP BY first_funder
        ORDER BY funded_wallet_count DESC, first_funder ASC
        LIMIT %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            columns = [column.name for column in cur.description]  # type: ignore
            return [dict(zip(columns, row)) for row in rows]



def get_wallet_profiles(wallet_addresses: list[str]) -> list[dict]:
    """Return profiles for a batch of wallet addresses."""

    if not wallet_addresses:
        return []

    sql = """
        SELECT
            wallet_address,
            first_fund_time,
            first_fund_amount,
            first_fund_token,
            first_funder,
            total_tx_count,
            in_degree,
            out_degree,
            forensic_status,
            is_contract,
            is_exchange
        FROM public.wallet_profiles
        WHERE wallet_address = ANY(%s);
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (wallet_addresses,))
            rows = cur.fetchall()
            columns = [column.name for column in cur.description]  # type: ignore
            return [dict(zip(columns, row)) for row in rows]
