from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class AnalysisContext:
    target_token_mint: str
    token_mint_date: str | None = None

    events: list[dict[str, Any]]
    profile_wallets: set[str]

    wallet_transfers: dict[str, dict[str, list[dict[str, Any]]]]
    wallet_features: dict[str, dict[str, Any]]

    first_fund_graph: nx.DiGraph
    aggregated_tx_graph: nx.DiGraph

    cache: dict[str, Any] = field(default_factory=dict)