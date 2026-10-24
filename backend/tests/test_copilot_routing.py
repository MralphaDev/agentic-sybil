"""Regression tests for Investigation Copilot routing and SQL allow-list."""

import unittest

from app.agent.copilot.router import router
from app.agent.copilot.service import _is_funding_question
from app.agent.copilot.database import _validate_sql


class CopilotRoutingTests(unittest.TestCase):
    def test_funder_of_wording_is_recognized(self):
        self.assertTrue(_is_funding_question("Who is the funder of 77m7xDRWsHQchZpbHj6SdS4dwj8F1KoNFJ2awxC1Y2NU?"))

    def test_second_hop_wording_is_recognized(self):
        self.assertTrue(_is_funding_question("Find the second hop in this wallet's funding chain"))

    def test_non_funding_wallet_question_is_not_misclassified(self):
        self.assertFalse(_is_funding_question("What token balances does this wallet have?"))

    def test_stream_endpoint_remains_registered(self):
        self.assertIn("/investigations/copilot/stream", {route.path for route in router.routes})

    def test_wallet_token_holdings_table_matches_sql_prompt_allowlist(self):
        query = _validate_sql("SELECT wallet_address, mint, amount FROM public.wallet_token_holdings LIMIT 5")
        self.assertIn("wallet_token_holdings", query)


if __name__ == "__main__":
    unittest.main()
