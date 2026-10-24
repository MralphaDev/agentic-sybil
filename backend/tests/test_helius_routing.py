from app.agent.helius_routing import is_helius_tool_error, select_wallet_action


def test_wallet_history_is_default_for_general_question():
    assert select_wallet_action("Show me this wallet's recent transactions") == "getWalletHistory"


def test_funding_question_routes_to_funding_source():
    assert select_wallet_action("Who was this wallet first funded by?") == "getWalletFundedBy"


def test_transfer_question_routes_to_transfers():
    assert select_wallet_action("Show transfers sent and received by this wallet") == "getWalletTransfers"


def test_token_balance_question_routes_to_token_balances():
    assert select_wallet_action("What are this wallet's token balances?") == "getTokenBalances"


def test_portfolio_question_routes_to_wallet_balances():
    assert select_wallet_action("Show this wallet's portfolio and USD value") == "getWalletBalances"


def test_native_balance_question_routes_to_sol_balance():
    assert select_wallet_action("What is this wallet's SOL balance?") == "getBalance"


def test_identity_question_routes_to_identity():
    assert select_wallet_action("Is this a known exchange wallet label?") == "getWalletIdentity"


def test_mcp_text_validation_error_is_detected_even_if_flag_false():
    result = "MCP error -32602: Input validation error: Invalid arguments for tool heliusWallet"
    assert is_helius_tool_error(result, is_error=False)


def test_mcp_success_text_is_not_error():
    assert not is_helius_tool_error('[{"type": "text", "text": "Wallet balance: 1 SOL"}]')


def test_mcp_error_flag_is_respected():
    assert is_helius_tool_error("unknown response", is_error=True)
