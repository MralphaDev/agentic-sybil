from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.context import AnalysisContext
from app.agent.nodes import (
    decision_node,
    initial_observation_node,
)
from app.agent.state import AgentState, MAX_INVESTIGATION_ROUNDS

from app.agent.tools.graph.top_funders import get_top_funders_tool
from app.agent.tools.graph.wallet_info import get_wallet_info
from app.agent.tools.graph.graph_connectivity import (
    build_graph_connectivity_tools,
)
from app.agent.tools.graph.graph_summary import (
    build_graph_summary_tools,
)
from app.agent.tools.graph.wallet_clustering import (
    build_wallet_clustering_tools,
)

from app.agent.tools.process_mining.filtered_dfg import (
    build_filtered_dfg_tools,
)
from app.agent.tools.process_mining.top_variants import (
    build_top_variants_tools,
)
from app.agent.tools.process_mining.variant_tools import (
    build_variant_tools,
)
from app.agent.tools.process_mining.variant_sell_analysis import (
    build_variant_sell_tools,
)
from app.agent.tools.process_mining.intermediary_analysis import (
    build_intermediary_tools,
)
from app.agent.tools.process_mining.coordinated_intermediary import (
    build_coordinated_intermediary_tools,
)


def build_agent_graph(context: AnalysisContext):
    graph = StateGraph(AgentState)

    clustering_tools = build_wallet_clustering_tools(context)
    clustering_tool_names = {tool.name for tool in clustering_tools}
    top_funders_tool_name = get_top_funders_tool.name

    tools = [
        # Graph tools
        *build_graph_connectivity_tools(context),
        *build_graph_summary_tools(context),
        *clustering_tools,

        # Process mining tools
        *build_filtered_dfg_tools(context),
        *build_top_variants_tools(context),
        *build_variant_tools(context),
        *build_variant_sell_tools(context),
        *build_intermediary_tools(context),
        *build_coordinated_intermediary_tools(context),

        get_top_funders_tool,
        get_wallet_info,
    ]

    tool_node = ToolNode(tools)

    def run_initial_observation(
        state: AgentState,
    ) -> dict[str, Any]:
        return {
            **initial_observation_node(context),
            "clustering_required": False,
            "clustering_done": False,
        }

    def run_decision(
        state: AgentState,
    ) -> dict[str, Any]:
        active_tools = tools

        # After top funders, require the clustering tool before
        # allowing the agent to continue its investigation.
        if state.get("clustering_required", False):
            active_tools = clustering_tools

        return decision_node(state, context, active_tools)

    def run_tools(
        state: AgentState,
    ) -> dict[str, Any]:
        result = tool_node.invoke(state)

        returned_messages = result.get("messages", [])
        called_names = {
            message.name
            for message in returned_messages
            if getattr(message, "name", None)
        }

        top_funders_called = top_funders_tool_name in called_names
        clustering_called = bool(called_names & clustering_tool_names)

        clustering_required = state.get("clustering_required", False)

        if top_funders_called and not clustering_called:
            clustering_required = True
        elif clustering_called:
            clustering_required = False

        return {
            **result,
            "investigation_round": state["investigation_round"] + 1,
            "clustering_required": clustering_required,
            "clustering_done": (
                state.get("clustering_done", False) or clustering_called
            ),
        }

    def route_after_decision(state: AgentState) -> str:
        if state["investigation_complete"]:
            return END

        if state["investigation_round"] >= MAX_INVESTIGATION_ROUNDS:
            return END

        last_message = state["messages"][-1] if state["messages"] else None

        if last_message and getattr(last_message, "tool_calls", []):
            return "tools"

        return END

    graph.add_node("initial_observation", run_initial_observation)
    graph.add_node("decision", run_decision)
    graph.add_node("tools", run_tools)

    graph.add_edge(START, "initial_observation")
    graph.add_edge("initial_observation", "decision")

    graph.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "tools": "tools",
            END: END,
        },
    )

    graph.add_edge("tools", "decision")

    return graph.compile()