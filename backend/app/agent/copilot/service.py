"""Streaming Investigation Copilot orchestration."""
import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator
from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.copilot.common import logger, MAX_HELIUS_CALLS, MAX_OUTPUT_TOKENS, MAX_QUESTION_CHARS, MAX_ROWS, _emit, _get_llm
from app.agent.copilot.database import _generate_sql, _get_investigation_context, _lookup_top_token_sellers, _lookup_wallet_direct, _lookup_wallet_funding_evidence, _run_readonly_query, _validate_sql
from app.agent.copilot.helius import _helius_mcp_fallback
from app.agent.copilot.models import CopilotRequest
from app.agent.copilot.prompts import COPILOT_SYSTEM

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

async def _needs_funding_trace(question: str) -> bool:
    """Classify the investigative objective semantically, not by a fixed phrase list."""
    try:
        response = await _get_llm(80).ainvoke([
            SystemMessage(content=(
                "Classify the user's investigative goal. Answer only YES or NO. "
                "Answer YES if they want to trace who funded a wallet, a funder's funder, "
                "an upstream predecessor, an ancestor/hop in a funding chain, or the earliest "
                "source of funds. Treat paraphrases and indirect wording as equivalent. "
                "Answer NO for unrelated balance, token, ownership, or general wallet questions."
            )),
            HumanMessage(content=question[:MAX_QUESTION_CHARS]),
        ])
        raw = response.content
        if isinstance(raw, list):
            raw = " ".join(part.get("text", "") for part in raw if isinstance(part, dict))
        return str(raw).strip().upper().startswith("YES")
    except Exception as exc:
        logger.warning("[Copilot] Funding-goal classification failed; using phrase fallback: %s", str(exc)[:160])
        return bool(re.search(
            r"\b(funder|funded by|funding|fund|predecessor|upstream|ancestor|hop|trace (?:the )?funds?)\b",
            question,
            re.IGNORECASE,
        ))


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
    extracted_address = wallet_match.group(1) if wallet_match else None
    # A mint address in a "who sold this token?" question is not a wallet address.
    # Route this common database question to a deterministic aggregate query.
    token_seller_query = bool(
        extracted_address
        and re.search(r"\b(sell|sold|seller|selling|sell off|dumped)\b", request.message, re.IGNORECASE)
        and re.search(r"\b(wallets?|token|mint|coin|holders?)\b", request.message, re.IGNORECASE)
    )
    wallet_address = None if token_seller_query else extracted_address
    database_has_transaction_rows = False
    if token_seller_query:
        yield _emit("progress", {"label": "Finding wallets that sold this token in PostgreSQL", "state": "active"})
        try:
            rows = await asyncio.to_thread(_lookup_top_token_sellers, extracted_address, 5)
            database_has_transaction_rows = bool(rows)
            # If the deterministic lookup finds no rows, let the general SQL planner
            # try alternate interpretations of how this ingestor records token mints.
            if not rows:
                sql, reason = await _generate_sql(request.message, context_text)
                if sql:
                    safe_sql = _validate_sql(sql)
                    yield _emit("progress", {"label": reason[:100], "state": "active"})
                    rows = await asyncio.to_thread(_run_readonly_query, safe_sql)
                    database_has_transaction_rows = bool(rows)
        except Exception as exc:
            sql_error = f"Token seller lookup failed: {type(exc).__name__}: {str(exc)[:180]}"
    elif wallet_address:
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
    helius_results: list[dict[str, Any]] = []
    explicit_helius_request = bool(re.search(
        r"\bhelius\b|\bmcp\b|\brpc\b|live on.chain|on.chain (?:history|data|transactions)|full transaction history|fetch transactions from chain",
        request.message, re.IGNORECASE,
    ))
    funding_question = bool(wallet_address and await _needs_funding_trace(request.message))
    if funding_question:
        # Investigate the funding graph from SQL first. The wallet's own profile/events
        # are not enough: every discovered predecessor becomes the next lookup target.
        yield _emit("progress", {"label": "Tracing upstream funding evidence in PostgreSQL", "state": "active"})
        address_pattern = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])")
        queue, queued, visited = [wallet_address], {wallet_address}, set()
        helius_unavailable = False
        while queue and len(visited) < 3:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            try:
                evidence = await asyncio.to_thread(_lookup_wallet_funding_evidence, current)
            except Exception as exc:
                logger.warning("[Copilot] SQL funding lookup failed for %s: %s", current, str(exc)[:180])
                evidence = {"wallet_profile": None, "earliest_incoming_events": []}
            profile = evidence.get("wallet_profile") or {}
            incoming = evidence.get("earliest_incoming_events") or []
            candidates = []
            profile_funder = profile.get("first_funder")
            if isinstance(profile_funder, str) and profile_funder != current:
                candidates.append(profile_funder)
            # If no indexed profile funder exists, derive candidates from incoming
            # transfer evidence. Prefer native/SOL transfers over arbitrary token receipts.
            if not candidates and incoming:
                def native_score(event: dict[str, Any]) -> int:
                    description = " ".join(str(event.get(key) or "") for key in (
                        "type", "translated_type", "kind", "from_token", "to_token"
                    )).lower()
                    return int("sol" in description or "native" in description)
                ordered = sorted(incoming, key=native_score, reverse=True)
                for event in ordered:
                    candidate = event.get("from_user_address")
                    if isinstance(candidate, str) and candidate != current and candidate not in candidates:
                        candidates.append(candidate)
                    if len(candidates) >= 3:
                        break
            rows.append({
                "funding_wallet_lookup": current,
                "wallet_profile": profile or None,
                "earliest_incoming_events": incoming,
                "candidate_funders": candidates,
            })
            yield _emit("progress", {"label": f"SQL checked wallet {current[:6]}…{current[-4:]}", "state": "active"})
            for candidate in candidates:
                if candidate not in visited and candidate not in queued:
                    queue.append(candidate)
                    queued.add(candidate)
            # Helius is a fallback, not a prerequisite: use it only if SQL cannot
            # identify a next hop, or if the user explicitly requested it.
            should_try_helius = explicit_helius_request or not candidates
            if should_try_helius and not helius_unavailable and len(helius_results) < MAX_HELIUS_CALLS:
                task = asyncio.create_task(_helius_mcp_fallback(
                    request.message, context_text,
                    wallet_address_override=current, action_override="getWalletFundedBy"
                ))
                try:
                    while not task.done():
                        done, _ = await asyncio.wait({task}, timeout=8)
                        if not done:
                            yield _emit("progress", {"label": "Helius is still checking the funding source…", "state": "active"})
                    result = await task
                except asyncio.CancelledError:
                    task.cancel()
                    raise
                if result:
                    helius_results.append({"wallet_address": current, "tool": result[0], "result": result[1]})
                    if result[0] == "HELIUS_MCP_ERROR":
                        helius_unavailable = True
                        yield _emit("progress", {"label": f"Helius MCP error: {str(result[1])[:900]}", "state": "error"})
                    else:
                        for candidate in address_pattern.findall(str(result[1])):
                            if candidate != current and candidate not in visited and candidate not in queued:
                                queue.append(candidate)
                                queued.add(candidate)
            if not candidates and not helius_results:
                yield _emit("progress", {"label": f"No upstream SQL record found for {current[:6]}…{current[-4:]}", "state": "active"})
        if helius_results:
            last = helius_results[-1]
            helius_result = (last["tool"], last["result"])
    else:
        database_has_transaction_rows = bool(rows) or database_has_transaction_rows
        # Empty database results are not, by themselves, a reason to call Helius.
        # Helius is useful when explicitly requested or when resolving a specific wallet.
        if explicit_helius_request or wallet_address:
            label = "Calling Helius MCP for live on-chain evidence" if explicit_helius_request else "Cross-checking wallet evidence with Helius"
            yield _emit("progress", {"label": label, "state": "active"})
            helius_task = asyncio.create_task(_helius_mcp_fallback(request.message, context_text))
            try:
                while not helius_task.done():
                    done, _ = await asyncio.wait({helius_task}, timeout=8)
                    if not done:
                        yield _emit("progress", {"label": "Helius is still retrieving on-chain data…", "state": "active"})
                helius_result = await helius_task
                if helius_result:
                    helius_results.append({"tool": helius_result[0], "result": helius_result[1]})
                if helius_result and helius_result[0] == "HELIUS_MCP_ERROR":
                    diagnostic = str(helius_result[1])[:1200]
                    logger.error("[Copilot] Helius MCP failure returned to request: %s", diagnostic)
                    yield _emit("progress", {"label": f"Helius MCP error: {diagnostic}", "state": "error"})
            except asyncio.CancelledError:
                helius_task.cancel()
                raise

    evidence = {
        "postgres_rows": rows,
        # Never expose raw SQL validation/database errors to the answer model.
        "postgres_lookup_failed": bool(sql_error),
        "helius_tool": helius_result[0] if helius_result else None,
        "helius_result": helius_result[1] if helius_result else None,
        "helius_calls": helius_results,
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
                "Related PostgreSQL events do not prove that the requested fact is known. Use all relevant returned sources, follow wallet addresses discovered in evidence, and distinguish missing data from a negative finding. For funding-chain questions, report each verified hop and its source. "
               
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
