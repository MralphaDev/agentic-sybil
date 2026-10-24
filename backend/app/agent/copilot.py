import asyncio
import json
import os
import re
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.sse_manager import encode_sse, get_run
from app.core.config import ENV_FILE, settings
from app.database.connection import get_connection

load_dotenv(ENV_FILE, override=False)

router = APIRouter(prefix="/investigations", tags=["Investigation Copilot"])
MAX_SQL_CALLS = 1
MAX_HELIUS_CALLS = 1
MAX_OUTPUT_TOKENS = 300
MAX_ROWS = 50
MAX_QUESTION_CHARS = 1200
SQL_TIMEOUT_MS = 5000

COPILOT_SYSTEM = """You are Investigation Copilot for a Solana wallet investigation.
Answer simple-to-medium complexity questions using the current investigation report
and read-only PostgreSQL data. Be concise, factual, and explicit when data is missing.
The investigation report is context, not proof beyond its stated evidence.
Do not reveal hidden reasoning. The UI displays operational progress events instead.
Never request secrets or suggest writing to the database. SQL is read-only.
Use only public.wallet_event_log and public.wallet_profiles, with columns provided
in the schema. Never query other schemas or tables. SQL must be a single SELECT or
WITH ... SELECT statement, with a LIMIT no greater than 50.
"""

SQL_SYSTEM = """Generate exactly one PostgreSQL SELECT query answering the user's question.
Return ONLY JSON: {"sql":"...","reason":"short operational description"}.
Allowed tables and columns:
public.wallet_event_log(wallet_address, signature, type, translated_type, event_time,
from_user_address, to_user_address, kind, from_token, from_amount, to_token, to_amount,
protocol, direction, amount, mint)
public.wallet_profiles(wallet_address, is_contract, is_exchange, forensic_status,
first_fund_time, first_fund_amount, first_fund_token, first_funder,
total_tx_count, in_degree, out_degree)
Rules: only SELECT or WITH ending in SELECT; only these two tables; never use
information_schema, pg_catalog, system functions, writes, DDL, multiple statements,
or SELECT *. Use explicit columns and LIMIT <= 50. If the question cannot be answered
from these tables, return {"sql":"","reason":"not available in PostgreSQL"}.
"""

DISALLOWED_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|"
    r"execute|prepare|deallocate|vacuum|analyze|refresh|pg_sleep|dblink|pg_read_file|lo_import|lo_export|"
    r"information_schema|pg_catalog)\b",
    re.IGNORECASE,
)
ALLOWED_TABLES = {"wallet_event_log", "wallet_profiles"}


class CopilotRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


def _emit(event_type: str, data: Any) -> str:
    return encode_sse({"type": event_type, "data": data})


def _get_llm(max_tokens: int = MAX_OUTPUT_TOKENS) -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=max_tokens,
        timeout=25,
        max_retries=1,
    )


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
    tables = re.findall(
        r"\b(?:from|join)\s+(?:public\.)?([a-z_][a-z0-9_]*)",
        query,
        re.IGNORECASE,
    )
    if not tables or any(table.lower() not in ALLOWED_TABLES for table in tables):
        raise ValueError("SQL must query only the approved public tables.")
    if re.search(r"\blimit\s+(\d+)", query, re.IGNORECASE):
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


def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


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


async def _helius_mcp_fallback(question: str, context_text: str) -> tuple[str, str] | None:
    """Make at most one read-only call to the official Helius MCP server."""
    api_key = os.getenv("HELIUS_API_KEY") or settings.HELIUS_API_KEY
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        return ("HELIUS_MCP_ERROR", f"Python MCP client is not installed: {exc}")

    # Windows requires cmd.exe to launch the npx.cmd shim; Unix can exec npx directly.
    if os.name == "nt":
        command = "cmd"
        args = ["/c", "npx", "-y", "helius-mcp@latest"]
    else:
        command = "npx"
        args = ["-y", "helius-mcp@latest"]
    params = StdioServerParameters(
        command=command,
        args=args,
        env={**os.environ, "HELIUS_API_KEY": api_key},
    )
    try:
        async with asyncio.timeout(40):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    tools = [
                        tool for tool in listed.tools
                        if not re.search(
                            r"send|sign|swap|stake|burn|close|write|submit|create|delete|update|approve|mint",
                            tool.name,
                            re.IGNORECASE,
                        )
                    ]
                    if not tools:
                        return ("HELIUS_MCP_ERROR", "Helius MCP started but exposed no read-only tools.")
                    wallet_match = re.search(
                        r"(?<![1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])",
                        question,
                    )
                    wallet_address = wallet_match.group(1) if wallet_match else None
                    if not wallet_address:
                        return ("HELIUS_MCP_ERROR", "No valid Solana wallet address was found for the Helius lookup.")

                    # Helius MCP uses router tools (heliusTransaction, heliusWallet, etc.).
                    # Their schemas require an "action" selector, so generic required-argument
                    # inference can incorrectly reject every valid tool. Prefer the documented
                    # parsed transaction-history action, then fall back to another compatible
                    # read-only action discovered from the live schema.
                    def schema_args(tool, action_name: str, preferred: dict[str, Any]) -> dict[str, Any] | None:
                        schema = tool.inputSchema or {}
                        properties = schema.get("properties") or {}
                        required = schema.get("required") or []
                        args: dict[str, Any] = {}
                        if "action" in properties:
                            args["action"] = action_name
                        for key, value in preferred.items():
                            if key in properties:
                                args[key] = value
                        # Supply conservative defaults for any other required parameters.
                        for key in required:
                            if key in args:
                                continue
                            prop = properties.get(key, {})
                            if prop.get("default") is not None:
                                args[key] = prop["default"]
                            elif prop.get("enum"):
                                args[key] = prop["enum"][0]
                            elif re.search(r"limit|max_results|page_size", key, re.I):
                                args[key] = min(50, int(prop.get("maximum", 50)))
                            else:
                                return None
                        return args

                    tool_by_name = {tool.name.lower(): tool for tool in tools}
                    selected = None
                    # Official helius-mcp exposes getTransactionHistory through heliusTransaction.
                    transaction_router = tool_by_name.get("heliustransaction")
                    if transaction_router:
                        schema = transaction_router.inputSchema or {}
                        properties = schema.get("properties") or {}
                        for action_name, preferred in (
                            ("getTransactionHistory", {
                                "address": wallet_address,
                                "mode": "parsed",
                                "limit": 10,
                                "detail": "standard",
                            }),
                            ("getTransactionHistory", {
                                "address": wallet_address,
                                "mode": "signatures",
                                "limit": 10,
                                "detail": "standard",
                            }),
                        ):
                            if "action" in properties and any(
                                key in properties for key in ("address", "walletAddress", "accountAddress")
                            ):
                                args = schema_args(transaction_router, action_name, preferred)
                                if args is not None:
                                    selected = (transaction_router.name, args)
                                    break

                    # Some server versions expose direct tools instead of router actions.
                    if selected is None:
                        candidates = []
                        for tool in tools:
                            name_text = f"{tool.name} {tool.description or ''}".lower()
                            schema = tool.inputSchema or {}
                            properties = schema.get("properties") or {}
                            address_key = next((
                                key for key in properties
                                if re.search(r"(^|_)(address|wallet|account|owner|pubkey|publickey)(_|$)", key, re.I)
                                or key.lower() in {
                                    "address", "walletaddress", "accountaddress",
                                    "publickey", "pubkey", "owneraddress",
                                }
                            ), None)
                            if not address_key:
                                continue
                            if not re.search(r"transaction|signature|history|activity|transfer", name_text):
                                continue
                            preferred = {address_key: wallet_address}
                            for key in properties:
                                if re.search(r"^(limit|max_results|page_size)$", key, re.I):
                                    preferred[key] = min(50, int(properties[key].get("maximum", 50)))
                            args = schema_args(tool, "", preferred)
                            if args is not None:
                                score = 5 if "transaction" in name_text else 0
                                score += 4 if "history" in name_text else 0
                                score += 3 if "signature" in name_text else 0
                                candidates.append((score, tool.name, args))
                        if candidates:
                            candidates.sort(key=lambda item: item[0], reverse=True)
                            _, tool_name, arguments = candidates[0]
                            selected = (tool_name, arguments)

                    if selected is None:
                        available = ", ".join(tool.name for tool in tools[:30])
                        return (
                            "HELIUS_MCP_ERROR",
                            f"No compatible read-only transaction-history tool found. Available tools: {available}",
                        )
                    name, arguments = selected
                    result = await session.call_tool(name, arguments)
                    if getattr(result, "isError", False):
                        return ("HELIUS_MCP_ERROR", json.dumps(result.content, ensure_ascii=False, default=str)[:1500])
                    serialized = json.dumps(result.content, ensure_ascii=False, default=str)
                    return name, serialized[:7000]
    except Exception as exc:
        # Preserve a concise diagnostic instead of silently hiding MCP startup/RPC failures.
        return ("HELIUS_MCP_ERROR", f"{type(exc).__name__}: {str(exc)[:1200]}")


async def _classify_intent(question: str) -> str:
    """Classify before any database or Helius work; output is deliberately tiny."""
    response = await _get_llm(100).ainvoke([
        SystemMessage(content=(
            "Classify the user's intent. Return exactly one word: 'lookup' if they need "
            "specific wallet/transaction/on-chain records or fresh database/RPC evidence; "
            "'report' if they ask about the existing investigation verdict, findings, or "
            "interpretation that can be answered from the saved report; 'general' for "
            "greetings, thanks, jokes, small talk, general programming/product questions, "
            "or anything unrelated to this investigation. Do not perform the task."
        )),
        HumanMessage(content=question[:MAX_QUESTION_CHARS]),
    ])
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(part.get("text", "") for part in raw if isinstance(part, dict))
    label = str(raw).strip().lower()
    if "lookup" in label:
        return "lookup"
    if "report" in label:
        return "report"
    return "general"


async def _answer_general_question(question: str) -> AsyncIterator[str]:
    """Answer non-investigation intent without database or Helius calls."""
    yield _emit("progress", {"label": "Answering directly — no database or RPC lookup needed", "state": "active"})
    async for chunk in _get_llm(MAX_OUTPUT_TOKENS).astream([
        SystemMessage(content=(
            "You are a concise, friendly assistant inside Investigation Copilot. "
            "This is general conversation, not an on-chain investigation request. "
            "Answer directly in at most 300 output tokens. Do not query databases or RPCs, "
            "and do not claim to have looked up investigation data."
        )),
        HumanMessage(content=question),
    ]):
        content = chunk.content
        if isinstance(content, str) and content:
            yield _emit("token", {"content": content})
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    yield _emit("token", {"content": part["text"]})

async def _answer_report_question(question: str, context_text: str) -> AsyncIterator[str]:
    """Answer from the saved investigation context without querying data sources."""
    yield _emit("progress", {"label": "Using the saved investigation report; no DB/RPC lookup needed", "state": "active"})
    async for chunk in _get_llm(MAX_OUTPUT_TOKENS).astream([
        SystemMessage(content=(
            "You are Investigation Copilot. Answer using only the supplied saved report/context. "
            "Be concise and direct, at most 300 output tokens. Do not query or imply you queried "
            "PostgreSQL or Helius. Distinguish observed evidence from interpretation and mention "
            "when the report does not contain enough evidence."
        )),
        HumanMessage(content=f"Saved investigation context:\n{context_text[:12000]}\n\nQuestion: {question}"),
    ]):
        content = chunk.content
        if isinstance(content, str) and content:
            yield _emit("token", {"content": content})
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    yield _emit("token", {"content": part["text"]})

async def _stream_answer(request: CopilotRequest) -> AsyncIterator[str]:
    # A wallet address is an explicit request for wallet-specific evidence.
    # Do not let the LLM intent classifier route it to report/general and skip lookups.
    has_wallet_address = bool(re.search(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])", request.message))
    # Confirm intent first. Casual/general requests must not touch DB or Helius.
    try:
        intent = "lookup" if has_wallet_address else await _classify_intent(request.message)
    except Exception:
        casual = re.compile(
            r"^(hi|hello|hey|thanks|thank you|thx|你好|嗨|哈喽|谢谢|谢了|在吗|早上好|晚安|哈哈)[!！?？。\s]*$",
            re.IGNORECASE,
        )
        intent = "general" if casual.match(request.message.strip()) else "investigation"

    if intent == "general":
        async for event in _answer_general_question(request.message):
            yield event
        yield _emit("done", {})
        return

    try:
        context_text, _ = _get_investigation_context(request.run_id)
    except HTTPException as exc:
        yield _emit("error", {"message": exc.detail})
        yield _emit("done", {})
        return

    if intent == "report":
        async for event in _answer_report_question(request.message, context_text):
            yield event
        yield _emit("done", {})
        return

    yield _emit("progress", {"label": "Reading investigation report", "state": "active"})

    sql = ""
    rows: list[dict[str, Any]] = []
    sql_error = None
    wallet_match = re.search(
        r"(?<![1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])",
        request.message,
    )
    wallet_address = wallet_match.group(1) if wallet_match else None
    database_has_transaction_rows = False
    if wallet_address:
        # Do not ask an LLM to construct the most important wallet lookup query.
        # Exact parameterized queries avoid schema hallucinations and address mismatches.
        yield _emit("progress", {"label": "Looking up the exact wallet address in PostgreSQL", "state": "active"})
        try:
            direct_data = await asyncio.to_thread(_lookup_wallet_direct, wallet_address)
            database_has_transaction_rows = bool(direct_data["recent_events"])
            if direct_data["wallet_profile"] is not None or direct_data["recent_events"]:
                rows = [{"wallet_profile": direct_data["wallet_profile"], "recent_events": direct_data["recent_events"]}]
        except Exception as exc:
            sql_error = f"Direct wallet lookup failed: {type(exc).__name__}: {str(exc)[:180]}"
    else:
        yield _emit("progress", {"label": "Planning a read-only PostgreSQL query", "state": "active"})
        try:
            sql, reason = await _generate_sql(request.message, context_text)
            if sql:
                safe_sql = _validate_sql(sql)
                yield _emit("progress", {"label": reason[:100], "state": "active"})
                rows = await asyncio.to_thread(_run_readonly_query, safe_sql)
                database_has_transaction_rows = bool(rows)
        except Exception as exc:
            sql_error = str(exc)[:240]

    helius_result = None
    # Explicit Helius/live-RPC requests must call Helius even when PostgreSQL has
    # some rows; indexed data is not a substitute for the requested live source.
    explicit_helius_request = bool(re.search(
        r"\bhelius\b|\bmcp\b|\brpc\b|live on.chain|on.chain (?:history|data|transactions)|"
        r"full transaction history|fetch transactions from chain",
        request.message,
        re.IGNORECASE,
    ))
    if explicit_helius_request or not database_has_transaction_rows:
        label = (
            "Calling Helius MCP for live on-chain evidence"
            if explicit_helius_request
            else "Database has no sufficient matching rows; checking Helius RPC"
        )
        yield _emit("progress", {"label": label, "state": "active"})
        # Keep the SSE connection active while the MCP subprocess starts and queries RPC.
        # Some browser/proxy paths drop streams that remain idle during a long await.
        helius_task = asyncio.create_task(_helius_mcp_fallback(request.message, context_text))
        try:
            while not helius_task.done():
                done, _ = await asyncio.wait({helius_task}, timeout=8)
                if not done:
                    yield _emit("progress", {
                        "label": "Helius is still retrieving on-chain data…",
                        "state": "active",
                    })
            helius_result = await helius_task
        except asyncio.CancelledError:
            helius_task.cancel()
            raise

    evidence = {
        "postgres_rows": rows,
        # Never expose raw SQL validation/database errors to the answer model.
        "postgres_lookup_failed": bool(sql_error),
        "helius_tool": helius_result[0] if helius_result else None,
        "helius_result": helius_result[1] if helius_result else None,
    }
    yield _emit("progress", {"label": "Summarizing available evidence", "state": "active"})
    yield _emit("start", {"message": "Answer"})
    try:
        messages = [
            SystemMessage(content=COPILOT_SYSTEM),
            HumanMessage(content=(
                f"Investigation report and context:\n{context_text}\n\n"
                f"User question:\n{request.message}\n\n"
                f"Evidence returned by tools (may be empty):\n"
                f"{json.dumps(evidence, ensure_ascii=False, default=str)[:12000]}\n\n"
                "Answer the user's question directly using returned evidence. Never show or suggest SQL, "
                "database queries, code, internal validation messages, or implementation details. "
                "If PostgreSQL has no matching rows or its query fails, use the Helius result if present. "
                "If both sources fail, state briefly that the lookup failed and summarize the source failure "
                "without exposing SQL or internal validation text. Never claim Helius succeeded unless a "
                "successful Helius tool result is present. A Helius tool result named HELIUS_MCP_ERROR is a failure, "
                "not on-chain evidence."
            )),
        ]
        async for chunk in _get_llm(MAX_OUTPUT_TOKENS).astream(messages):
            content = chunk.content
            if isinstance(content, str) and content:
                yield _emit("token", {"content": content})
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                        yield _emit("token", {"content": part["text"]})
    except Exception as exc:
        yield _emit("error", {"message": f"DeepSeek request failed: {str(exc)[:200]}"})
    yield _emit("done", {})


@router.post("/copilot/stream")
async def copilot_stream(request: CopilotRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_answer(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
