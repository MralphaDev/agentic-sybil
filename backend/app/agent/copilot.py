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
MAX_SQL_CALLS = 2
MAX_HELIUS_CALLS = 1
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
first_active_time, first_fund_time, first_fund_amount, first_fund_token, first_funder,
total_tx_count, in_degree, out_degree, processed_at, updated_at)
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


def _get_llm(max_tokens: int = 900) -> ChatOpenAI:
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
    response = await _get_llm(350).ainvoke([
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
    except ImportError:
        return None

    params = StdioServerParameters(
        command="npx",
        args=["-y", "helius-mcp@latest"],
        env={**os.environ, "HELIUS_API_KEY": api_key},
    )
    try:
        async with asyncio.timeout(14):
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
                        return None
                    tool_catalog = [
                        {"name": tool.name, "description": (tool.description or "")[:350],
                         "inputSchema": tool.inputSchema}
                        for tool in tools
                    ]
                    selection = await _get_llm(300).ainvoke([
                        SystemMessage(content=(
                            "Choose at most one read-only Helius MCP tool for the user question. "
                            "Return only JSON {\"name\":\"tool name\",\"arguments\":{...}}. "
                            "Only use arguments supported by that tool's input schema. If no tool "
                            "is suitable, return {\"name\":\"\",\"arguments\":{}}. "
                            "Do not investigate repeatedly."
                        )),
                        HumanMessage(content=(
                            f"Question: {question}\nInvestigation context: {context_text[:2500]}\n"
                            f"Available read-only tools: {json.dumps(tool_catalog, ensure_ascii=False)}"
                        )),
                    ])
                    raw = selection.content
                    if isinstance(raw, list):
                        raw = "".join(part.get("text", "") for part in raw if isinstance(part, dict))
                    match = re.search(r"\{.*\}", str(raw), re.DOTALL)
                    if not match:
                        return None
                    chosen = json.loads(match.group(0))
                    name = chosen.get("name")
                    if name not in {tool.name for tool in tools}:
                        return None
                    result = await session.call_tool(name, chosen.get("arguments") or {})
                    if getattr(result, "isError", False):
                        return None
                    serialized = json.dumps(result.content, ensure_ascii=False, default=str)
                    return name, serialized[:7000]
    except Exception:
        # RPC fallback is best-effort; never leave the Copilot running indefinitely.
        return None


async def _stream_answer(request: CopilotRequest) -> AsyncIterator[str]:
    try:
        context_text, _ = _get_investigation_context(request.run_id)
    except HTTPException as exc:
        yield _emit("error", {"message": exc.detail})
        yield _emit("done", {})
        return

    yield _emit("progress", {"label": "Reading investigation report", "state": "active"})
    yield _emit("progress", {"label": "Planning a read-only PostgreSQL query", "state": "active"})

    sql = ""
    rows: list[dict[str, Any]] = []
    sql_error = None
    try:
        sql, reason = await _generate_sql(request.message, context_text)
        if sql:
            safe_sql = _validate_sql(sql)
            yield _emit("progress", {"label": reason[:100], "state": "active"})
            rows = await asyncio.to_thread(_run_readonly_query, safe_sql)
    except Exception as exc:
        sql_error = str(exc)[:240]

    helius_result = None
    if not rows:
        yield _emit("progress", {"label": "Database has no sufficient matching rows; checking Helius RPC", "state": "active"})
        helius_result = await _helius_mcp_fallback(request.message, context_text)

    evidence = {
        "postgres_rows": rows,
        "postgres_error": sql_error,
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
                "Answer the question directly. If database and RPC evidence are unavailable, "
                "say so clearly and offer a specific query/address that would make it answerable. "
                "Do not claim RPC was queried successfully unless a tool result is present."
            )),
        ]
        async for chunk in _get_llm(900).astream(messages):
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
