
import networkx as nx

from app.agent.context import AnalysisContext
from app.agent.graph import build_agent_graph
from app.agent.state import AgentState
from app.database.connection import open_pool, close_pool
from app.database.queries import get_wallet_events

def main() -> None:
    context = AnalysisContext(
        target_token_mint="test_mint",
        events=get_wallet_events(),
        profile_wallets=set(),
        wallet_transfers={},
        wallet_features={},
        first_fund_graph=nx.DiGraph(),
        aggregated_tx_graph=nx.DiGraph(),
    )

    graph = build_agent_graph(context)

    initial_state: AgentState = {
        "messages": [],
        "initial_observation": {},
        "next_action": "",
        "hypotheses": [],
        "findings": [],
        "evidence": [],
        "investigation_round": 0,
        "investigation_complete": False,
    }

    open_pool()

    try:
        print("Running agent investigation...")

        result = graph.invoke(initial_state)

        print("\nInvestigation completed.")
        print("Rounds:", result["investigation_round"])
        print("Complete:", result["investigation_complete"])
        print("Initial observation:", result["initial_observation"])
        print("Findings:", result["findings"])
        print("Evidence:", result["evidence"])

        final_message = (
            result["messages"][-1].content
            if result["messages"]
            and not getattr(result["messages"][-1], "tool_calls", [])
            else None
        )
        print("Final response:", final_message)

    finally:
        close_pool()


if __name__ == "__main__":
    main()
