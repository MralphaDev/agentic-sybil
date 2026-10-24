"""Read-only PostgreSQL lookups and SQL planning for Investigation Copilot."""

import json
import re
from typing import Any
from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.copilot.common import MAX_ROWS, SQL_TIMEOUT_MS, _json_safe, _get_llm
from app.agent.copilot.prompts import DISALLOWED_SQL, ALLOWED_TABLES, SQL_SYSTEM
from app.agent.sse_manager import get_run
from app.database.connection import get_connection

def _validate_sql(sql: str) -> str:
    query = sql.strip()
    if query.endswith(";"):
        query = query[:-1].rstrip()
    if not query or ";" in query:
        raise ValueError("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", query, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    if DISALLOWED_SQL.search(query):
        raise ValueError("The generated SQL contains a prohibited operation.")
    if re.search(r"\bselect\s+\*|\b[a-z_][a-z0-9_]*\.\*", query, re.IGNORECASE):
        raise ValueError("SELECT * is not allowed.")
    # Permit references to CTEs while ensuring every physical table is allowlisted.
    cte_names = {
        name.lower()
        for name in re.findall(
            r"(?:\bwith\s+|,\s*)(?:recursive\s+)?([a-z_][a-z0-9_]*)\s+as\s*\(",
            query,
            re.IGNORECASE,
        )
    }
    tables = re.findall(
        r"\b(?:from|join)\s+(?:public\.)?([a-z_][a-z0-9_]*)",
        query,
        re.IGNORECASE,
    )
    if not tables or any(table.lower() not in ALLOWED_TABLES and table.lower() not in cte_names for table in tables):
        raise ValueError("SQL must query only the approved public tables or query-local CTEs.")
    limit_match = re.search(r"\blimit\s+(\d+)", query, re.IGNORECASE)
    if limit_match:
        requested_limit = int(limit_match.group(1))
        if requested_limit > MAX_ROWS:
            query = re.sub(
                r"\blimit\s+\d+",
                f"LIMIT {MAX_ROWS}",
                query,
                count=1,
                flags=re.IGNORECASE,
            )
    else:
        query += f" LIMIT {MAX_ROWS}"
    return query

def _run_readonly_query(sql: str) -> list[dict[str, Any]]:
    # The transaction-level read-only setting is enforced by PostgreSQL itself.
    with get_connection() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(f"SET LOCAL statement_timeout = '{SQL_TIMEOUT_MS}ms'")
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [column.name for column in (cur.description or [])]
                rows = cur.fetchmany(MAX_ROWS)
                return [
                    {column: _json_safe(value) for column, value in zip(columns, row)}
                    for row in rows
                ]


def _lookup_top_token_sellers(token_mint: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Rank wallets by sell events, optionally scoped to a token mint."""
    limit = max(1, min(int(limit), 50))
    with get_connection() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(f"SET LOCAL statement_timeout = '{SQL_TIMEOUT_MS}ms'")
            with conn.cursor() as cur:
                if token_mint:
                    query = """
                        SELECT wallet_address, COUNT(DISTINCT signature) AS sell_count,
                               MIN(event_time) AS first_sell_time,
                               MAX(event_time) AS last_sell_time
                        FROM public.wallet_event_log
                        WHERE LOWER(TRIM(translated_type)) = 'sell'
                          AND mint = %s
                        GROUP BY wallet_address
                        ORDER BY sell_count DESC, wallet_address
                        LIMIT %s
                    """
                    cur.execute(query, (token_mint, limit))
                    columns = [column.name for column in (cur.description or [])]
                    rows = cur.fetchall()
                    if not rows:
                        query = """
                            SELECT wallet_address, COUNT(DISTINCT signature) AS sell_count,
                                   MIN(event_time) AS first_sell_time,
                                   MAX(event_time) AS last_sell_time
                            FROM public.wallet_event_log
                            WHERE LOWER(TRIM(translated_type)) = 'sell'
                              AND (from_token = %s OR to_token = %s)
                            GROUP BY wallet_address
                            ORDER BY sell_count DESC, wallet_address
                            LIMIT %s
                        """
                        cur.execute(query, (token_mint, token_mint, limit))
                        columns = [column.name for column in (cur.description or [])]
                        rows = cur.fetchall()
                else:
                    query = """
                        SELECT wallet_address, COUNT(DISTINCT signature) AS sell_count,
                               MIN(event_time) AS first_sell_time,
                               MAX(event_time) AS last_sell_time
                        FROM public.wallet_event_log
                        WHERE LOWER(TRIM(translated_type)) = 'sell'
                        GROUP BY wallet_address
                        ORDER BY sell_count DESC, wallet_address
                        LIMIT %s
                    """
                    cur.execute(query, (limit,))
                    columns = [column.name for column in (cur.description or [])]
                    rows = cur.fetchall()
            return [
                {column: _json_safe(value) for column, value in zip(columns, row)}
                for row in rows
            ]


def _lookup_wallet_direct(wallet_address: str) -> dict[str, Any]:
    """Deterministically look up a specific wallet without LLM-generated SQL."""
    with get_connection() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(f"SET LOCAL statement_timeout = '{SQL_TIMEOUT_MS}ms'")

            profile_cursor = conn.execute(
                """
                SELECT wallet_address, is_contract, is_exchange, forensic_status,
                       first_fund_time, first_fund_amount, first_fund_token,
                       first_funder, total_tx_count, in_degree, out_degree
                FROM public.wallet_profiles
                WHERE wallet_address = %s
                LIMIT 1
                """,
                (wallet_address,),
            )
            profile_columns = [column.name for column in profile_cursor.description or []]
            profile_row = profile_cursor.fetchone()
            profile = (
                {column: _json_safe(value) for column, value in zip(profile_columns, profile_row)}
                if profile_row else None
            )

            event_cursor = conn.execute(
                """
                SELECT wallet_address, signature, type, translated_type, event_time,
                       from_user_address, to_user_address, kind, from_token, from_amount,
                       to_token, to_amount, protocol, direction, amount, mint
                FROM public.wallet_event_log
                WHERE wallet_address = %s
                   OR from_user_address = %s
                   OR to_user_address = %s
                ORDER BY event_time DESC NULLS LAST
                LIMIT %s
                """,
                (wallet_address, wallet_address, wallet_address, MAX_ROWS),
            )
            event_columns = [column.name for column in event_cursor.description or []]
            events = [
                {column: _json_safe(value) for column, value in zip(event_columns, row)}
                for row in event_cursor.fetchall()
            ]
            return {"wallet_profile": profile, "recent_events": events}


def _lookup_wallet_funding_evidence(wallet_address: str) -> dict[str, Any]:
    """Find a wallet's recorded funder plus earliest incoming events, without relying on Helius."""
    with get_connection() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute(f"SET LOCAL statement_timeout = '{SQL_TIMEOUT_MS}ms'")
            profile_cursor = conn.execute(
                """
                SELECT wallet_address, first_funder, first_fund_time, first_fund_amount,
                       first_fund_token, total_tx_count, is_exchange, forensic_status
                FROM public.wallet_profiles
                WHERE wallet_address = %s
                LIMIT 1
                """,
                (wallet_address,),
            )
            profile_columns = [column.name for column in profile_cursor.description or []]
            profile_row = profile_cursor.fetchone()
            profile = (
                {column: _json_safe(value) for column, value in zip(profile_columns, profile_row)}
                if profile_row else None
            )
            event_cursor = conn.execute(
                """
                SELECT wallet_address, signature, type, translated_type, event_time,
                       from_user_address, to_user_address, kind, from_token, from_amount,
                       to_token, to_amount, protocol, direction, amount, mint
                FROM public.wallet_event_log
                WHERE to_user_address = %s
                  AND from_user_address IS NOT NULL
                  AND from_user_address <> %s
                ORDER BY event_time ASC NULLS LAST
                LIMIT 20
                """,
                (wallet_address, wallet_address),
            )
            columns = [column.name for column in event_cursor.description or []]
            incoming = [
                {column: _json_safe(value) for column, value in zip(columns, row)}
                for row in event_cursor.fetchall()
            ]
            return {"wallet_profile": profile, "earliest_incoming_events": incoming}


def _get_investigation_context(run_id: str) -> tuple[str, dict[str, Any]]:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Investigation run not found.")
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Investigation is not complete yet.")
    result = run.result or {}
    analysis = result.get("analysis") or {}
    investigation = analysis.get("investigation") or {}
    final_response = investigation.get("final_response")
    if not final_response:
        final_response = (
            "No final investigation report was saved for this run. "
            "Use the stored process-mining and wallet data; do not invent a verdict."
        )
    compact = {
        "token_mint": result.get("ingestion", {}).get("token_address"),
        "analysis_keys": list(analysis.keys()),
        "process_mining_result": analysis.get("process_mining_result"),
        "investigation_final_response": final_response,
    }
    # Keep the supplied context bounded; raw event logs and graph payloads are not sent.
    context_text = json.dumps(compact, ensure_ascii=False, default=str)[:14000]
    return context_text, compact

async def _generate_sql(question: str, context_text: str) -> tuple[str, str]:
    response = await _get_llm(220).ainvoke([
        SystemMessage(content=SQL_SYSTEM),
        HumanMessage(content=f"Investigation context:\n{context_text[:5000]}\n\nQuestion: {question}"),
    ])
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(part.get("text", "") for part in raw if isinstance(part, dict))
    text = str(raw).strip()
    text = re.sub(r"^\x60{3}(?:json)?\s*|\s*\x60{3}$", "", text, flags=re.IGNORECASE)
    try:
        parsed = json.loads(text)
        return str(parsed.get("sql", "")).strip(), str(parsed.get("reason", "Querying the database"))
    except (json.JSONDecodeError, AttributeError):
        raise ValueError("Could not safely interpret the SQL plan.")
