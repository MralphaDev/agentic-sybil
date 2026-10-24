"""Pure helpers for routing read-only Helius wallet investigation requests."""
import re


def select_wallet_action(question: str) -> str:
    """Choose a read-only Helius Wallet action from the user's intent."""
    q = question.lower()
    if re.search(r"\b(identity|who owns|owner of|label|exchange|known wallet|wallet label)\b", q):
        return "getWalletIdentity"
    if re.search(r"\b(funded by|funding source|first fund|who funded|funding wallet)\b", q):
        return "getWalletFundedBy"
    if re.search(r"\b(transfers?|sent|received|counterpart(y|ies)|inbound|outbound)\b", q):
        return "getWalletTransfers"
    if re.search(r"\b(token balances?|spl balances?|token holdings?|holdings|portfolio|usd value|asset balances?)\b", q):
        return "getWalletBalances" if re.search(r"\b(portfolio|usd value|total value)\b", q) else "getTokenBalances"
    if re.search(r"\b(sol balance|native balance|how much sol|sol amount|wallet balance|balance of)\b", q):
        return "getBalance"
    return "getWalletHistory"


def is_helius_tool_error(serialized_result: str, is_error: bool = False) -> bool:
    """Detect errors returned as text even if MCP's isError flag is false."""
    return is_error or bool(
        re.search(r"MCP error -\d+|Input validation error|Invalid arguments for tool", serialized_result, re.I)
    )
