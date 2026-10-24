"""Read-only Helius MCP access for Investigation Copilot."""
import asyncio
import json
import logging
import os
import re
from typing import Any
from app.core.config import settings
from app.agent.copilot.common import logger

def _get_tool_schema(tool: Any) -> dict[str, Any]:
    """Read MCP tool input schemas across Python SDK model naming variants."""
    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema", None)

    def as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        dump = getattr(value, "model_dump", None)
        if callable(dump):
            try:
                data = dump(by_alias=True)
            except TypeError:
                data = dump()
            if isinstance(data, dict):
                return data
        return {}

    result = as_dict(schema)
    if result:
        return result
    dump = getattr(tool, "model_dump", None)
    if callable(dump):
        try:
            data = dump(by_alias=True)
        except TypeError:
            data = dump()
        if isinstance(data, dict):
            return as_dict(data.get("inputSchema") or data.get("input_schema"))
    return {}


async def _helius_mcp_fallback(question: str, context_text: str, wallet_address_override: str | None = None, action_override: str | None = None) -> tuple[str, str] | None:
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
    child_env = dict(os.environ)
    # Avoid passing a None value to the subprocess environment when the key is
    # provided through the Helius user's config file instead of an env variable.
    if api_key:
        child_env["HELIUS_API_KEY"] = api_key
    params = StdioServerParameters(
        command=command,
        args=args,
        env=child_env,
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
                    wallet_address = wallet_address_override or (wallet_match.group(1) if wallet_match else None)
                    if not wallet_address:
                        return ("HELIUS_MCP_ERROR", "No valid Solana wallet address was found for the Helius lookup.")

                    # Helius MCP uses router tools (heliusTransaction, heliusWallet, etc.).
                    # Their schemas require an "action" selector, so generic required-argument
                    # inference can incorrectly reject every valid tool. Prefer the documented
                    # parsed transaction-history action, then fall back to another compatible
                    # read-only action discovered from the live schema.
                    def schema_args(tool, action_name: str, preferred: dict[str, Any]) -> dict[str, Any] | None:
                        schema = _get_tool_schema(tool)
                        properties = schema.get("properties") or {}
                        required = schema.get("required") or []
                        args: dict[str, Any] = {}
                        if "action" in properties:
                            action_enum = properties["action"].get("enum") or []
                            if action_name not in action_enum and action_enum:
                                # Tool versions can rename actions. Choose only an action
                                # explicitly advertised by the running server's schema.
                                aliases = {
                                    "getTransactionHistory": (
                                        "getTransactionHistory", "getTransactionsByAddress",
                                        "getTransactionsForAddress", "getWalletHistory",
                                    )
                                }
                                action_name = next(
                                    (candidate for candidate in aliases.get(action_name, (action_name,))
                                     if candidate in action_enum),
                                    action_enum[0] if action_enum else action_name,
                                )
                            if action_name:
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
                    # Route wallet-specific questions to the relevant read-only Wallet API
                    # action. Keep transaction history as the default when no clearer intent
                    # is expressed; never expose wallet-write actions through this fallback.
                    q = question.lower()
                    if action_override:
                        wallet_action = action_override
                    elif re.search(r"\b(identity|who owns|owner of|label|exchange|known wallet|wallet label)\b", q):
                        wallet_action = "getWalletIdentity"
                    elif re.search(r"\b(funded by|funder of|funder for|funding source|funding chain|first fund|who funded|funding wallet|upstream funder|second hop)\b", q):
                        wallet_action = "getWalletFundedBy"
                    elif re.search(r"\b(transfers?|sent|received|counterpart(y|ies)|inbound|outbound)\b", q):
                        wallet_action = "getWalletTransfers"
                    elif re.search(r"\b(token balances?|spl balances?|token holdings?|holdings|portfolio|usd value|asset balances?)\b", q):
                        wallet_action = "getWalletBalances" if re.search(r"\b(portfolio|usd value|total value)\b", q) else "getTokenBalances"
                    elif re.search(r"\b(sol balance|native balance|how much sol|sol amount|wallet balance|balance of)\b", q):
                        wallet_action = "getBalance"
                    else:
                        wallet_action = "getWalletHistory"

                    preferred_router_order = (
                        [("heliuswallet", wallet_action)]
                        if wallet_action != "getWalletHistory"
                        else [("heliuswallet", "getWalletHistory"), ("heliustransaction", "getTransactionHistory")]
                    )
                    for router_name, action_name in preferred_router_order:
                        router = tool_by_name.get(router_name)
                        if not router:
                            continue
                        schema = _get_tool_schema(router)
                        properties = schema.get("properties") or {}
                        address_key = next((
                            key for key in properties
                            if key.lower() in {"address", "walletaddress", "accountaddress", "owneraddress", "pubkey", "publickey"}
                        ), None)
                        if not address_key or "action" not in properties:
                            continue
                        preferred = {
                            address_key: wallet_address,
                            "detail": "standard",
                            "_feedback": f"Read-only wallet investigation: {action_name}",
                            "_feedbackTool": f"{router.name}.{action_name}",
                            "_model": "deepseek-chat",
                        }
                        for key in properties:
                            if re.search(r"^(limit|max_results|page_size)$", key, re.I):
                                preferred[key] = min(5, int(properties[key].get("maximum", 5)))
                        args = schema_args(router, action_name, preferred)
                        if args is not None:
                            selected = (router.name, args)
                            break

                    # Official Helius MCP docs define these as routed tools whose
                    # documented action is passed in the "action" argument. If the
                    # SDK's Tool object does not expose a readable JSON schema, still
                    # attempt the documented read-only call shape; any server-side
                    # validation error will be returned and logged below.
                    if selected is None:
                        for router_name, action_name in (
                            ("heliuswallet", "getWalletHistory"),
                            ("heliustransaction", "getTransactionHistory"),
                        ):
                            router = tool_by_name.get(router_name)
                            if router:
                                selected = (
                                    router.name,
                                    {
                                        "action": action_name,
                                        "address": wallet_address,
                                        "detail": "standard",
                                        "_feedback": f"Read-only wallet investigation: {action_name}",
                                        "_feedbackTool": f"{router.name}.{action_name}",
                                        "_model": "deepseek-chat",
                                    },
                                )
                                logger.warning(
                                    "[Helius MCP] Tool schema unavailable or unrecognized; "
                                    "trying documented routed call tool=%s action=%s",
                                    router.name,
                                    action_name,
                                )
                                break

                    # Some server versions expose direct tools instead of router actions.
                    if selected is None:
                        candidates = []
                        for tool in tools:
                            name_text = f"{tool.name} {tool.description or ''}".lower()
                            schema = _get_tool_schema(tool)
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
                            inferred_action = (
                                "getWalletHistory" if "action" in properties and "heliuswallet" in tool.name.lower()
                                else "getTransactionHistory" if "action" in properties and "transaction" in name_text
                                else ""
                            )
                            args = schema_args(tool, inferred_action, preferred)
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
                        # Include schema diagnostics for the two expected router tools so
                        # the next failure identifies the live MCP shape instead of guessing.
                        diagnostics = []
                        for tool in tools:
                            if tool.name.lower() in {"heliuswallet", "heliustransaction"}:
                                schema = _get_tool_schema(tool)
                                diagnostics.append({
                                    "tool": tool.name,
                                    "schema_keys": list(schema.keys()),
                                    "property_names": list((schema.get("properties") or {}).keys()),
                                    "required": schema.get("required") or [],
                                })
                        available = ", ".join(tool.name for tool in tools[:30])
                        logger.error(
                            "[Helius MCP] No compatible history tool. Schema diagnostics: %s",
                            json.dumps(diagnostics, ensure_ascii=False, default=str),
                        )
                        return (
                            "HELIUS_MCP_ERROR",
                            f"No compatible read-only transaction-history tool found. Available tools: {available}. "
                            f"Schema diagnostics: {json.dumps(diagnostics, ensure_ascii=False, default=str)[:2500]}",
                        )
                    name, arguments = selected
                    action = arguments.get("action", "<direct-tool>")
                    # Use warning-level diagnostics so these are visible even when
                    # the application's logger is configured above INFO.
                    logger.warning(
                        "[Helius MCP] Calling tool=%s action=%s arguments=%r",
                        name,
                        action,
                        arguments,
                    )
                    try:
                        result = await session.call_tool(name, arguments)
                    except Exception:
                        logger.exception(
                            "[Helius MCP] call_tool raised; tool=%s action=%s",
                            name,
                            action,
                        )
                        raise

                    serialized = json.dumps(result.content, ensure_ascii=False, default=str)
                    is_error = getattr(result, "isError", False)
                    logger.warning(
                        "[Helius MCP] call_tool returned tool=%s action=%s isError=%r "
                        "content=%s",
                        name,
                        action,
                        is_error,
                        serialized[:5000],
                    )
                    # Some Helius MCP server versions wrap validation failures in a
                    # text content block while leaving the MCP-level isError flag false.
                    returned_validation_error = bool(
                        re.search(r"MCP error -\d+|Input validation error|Invalid arguments for tool", serialized, re.I)
                    )
                    if is_error or returned_validation_error:
                        detail = serialized[:5000]
                        logger.error(
                            "[Helius MCP] Tool returned isError=true; tool=%s action=%s result=%s",
                            name,
                            action,
                            detail,
                        )
                        return ("HELIUS_MCP_ERROR", detail)
                    logger.warning(
                        "[Helius MCP] Tool succeeded; tool=%s response_chars=%d",
                        name,
                        len(serialized),
                    )
                    return name, serialized[:7000]
    except Exception as exc:
        # TaskGroup/ExceptionGroup can hide the underlying transport or subprocess
        # failure. Log the full traceback and flatten nested exceptions for the UI.
        def describe_exception(error: BaseException, depth: int = 0) -> list[str]:
            prefix = "  " * depth
            lines = [f"{prefix}{type(error).__name__}: {str(error)[:1000]}"]
            nested = getattr(error, "exceptions", None)
            if nested:
                for child in nested[:10]:
                    lines.extend(describe_exception(child, depth + 1))
            cause = getattr(error, "__cause__", None)
            context = getattr(error, "__context__", None)
            if cause and not nested:
                lines.extend(describe_exception(cause, depth + 1))
            elif context and not nested:
                lines.extend(describe_exception(context, depth + 1))
            return lines

        detail = "\n".join(describe_exception(exc))[:5000]
        logger.exception("[Helius MCP] Request failed; flattened cause: %s", detail)
        print(f"\n[Helius MCP ERROR]\n{detail}", flush=True)
        return ("HELIUS_MCP_ERROR", detail)
