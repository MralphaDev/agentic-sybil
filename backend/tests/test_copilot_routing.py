"""Regression tests for goal-driven Investigation Copilot routing."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.agent.copilot.routes import router
from app.agent.copilot.service import _needs_funding_trace
from app.agent.copilot.database import _validate_sql


class CopilotRoutingTests(unittest.TestCase):
    def test_stream_endpoint_remains_registered(self):
        self.assertIn("/investigations/copilot/stream", {route.path for route in router.routes})

    def test_wallet_token_holdings_table_matches_sql_prompt_allowlist(self):
        query = _validate_sql("SELECT wallet_address, mint, amount FROM public.wallet_token_holdings LIMIT 5")
        self.assertIn("wallet_token_holdings", query)


class FundingGoalClassificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_indirect_predecessor_wording_uses_semantic_classifier(self):
        # Deliberately avoids the old hard-coded trigger phrases.
        fake_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="YES")))
        with patch("app.agent.copilot.service._get_llm", return_value=fake_llm):
            self.assertTrue(await _needs_funding_trace(
                "Which account supplied the account that originally supplied this wallet?"
            ))

    async def test_second_hop_paraphrase_is_classified_as_funding_trace(self):
        fake_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="YES")))
        with patch("app.agent.copilot.service._get_llm", return_value=fake_llm):
            self.assertTrue(await _needs_funding_trace("Find the upstream ancestor two transfers before this address"))

    async def test_unrelated_balance_question_is_not_funding_trace(self):
        fake_llm = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="NO")))
        with patch("app.agent.copilot.service._get_llm", return_value=fake_llm):
            self.assertFalse(await _needs_funding_trace("What token balances does this wallet have?"))


if __name__ == "__main__":
    unittest.main()
