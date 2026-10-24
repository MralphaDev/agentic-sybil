
from typing import Any

import networkx as nx
from langchain_core.tools import tool

from app.agent.context import AnalysisContext


def build_graph_summary_tools(context: AnalysisContext):
    @tool
    def get_graph_summary() -> dict[str, Any]:
        """Get basic structural statistics for the first-funding graph and
        aggregated transaction graph.

        Returns node count, edge count, connected component count,
        largest component size, isolated wallet count, and graph direction.
        Does not return individual wallet addresses or edges.
        """
        def summarize(
            graph: nx.DiGraph,
            graph_name: str,
        ) -> dict[str, Any]:
            undirected_graph = graph.to_undirected()
            components = list(
                nx.connected_components(undirected_graph)
            )

            return {
                "graph_name": graph_name,
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
                "connected_component_count": len(components),
                "largest_component_size": max(
                    (len(component) for component in components),
                    default=0,
                ),
                "isolated_wallet_count": len(
                    list(nx.isolates(graph))
                ),
                "is_directed": graph.is_directed(),
            }

        return {
            "first_fund_graph": summarize(
                context.first_fund_graph,
                "first_fund_graph",
            ),
            "aggregated_tx_graph": summarize(
                context.aggregated_tx_graph,
                "aggregated_tx_graph",
            ),
        }

    return [get_graph_summary]
