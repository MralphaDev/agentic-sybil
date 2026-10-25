
from typing import Any

import pandas as pd
import pm4py
from langchain_core.tools import tool

from app.agent.context import AnalysisContext
from app.process_mining.event_mapping.event_mapping import map_event_action
from app.process_mining.dfg.stochastic_dfg_analysis import (
    add_transition_probabilities,
)


EXCLUDED_ACTIVITIES = {
    "create_account",
    "create_token_account",
    "transfer",
    "swap",
    "unknown",
    "receive_non_target_token",
    "transfer_non_target_token",
}


def _discover_raw_dfg(context: AnalysisContext) -> dict[str, Any]:
    """Discover and cache the raw DFG without writing files."""

    cache_key = "agent_raw_dfg_result"

    if cache_key in context.cache:
        return context.cache[cache_key]

    if not context.events:
        result = {
            "edges": [],
            "start_activities": {},
            "end_activities": {},
        }
        context.cache[cache_key] = result
        return result

    df = pd.DataFrame(context.events)

    # Reuse the existing event-to-action mapping.
    df["action"] = df.apply(
        lambda row: map_event_action(
            row.to_dict(),
            target_token_mint=context.target_token_mint,
        ),
        axis=1,
    )

    # Reuse the dust filtering rule from run_process_mining().
    df = df.loc[
        ~(
            df["type"].eq("transfer")
            & (
                pd.to_numeric(df["amount"], errors="coerce")
                < 0.001
            )
        )
    ].copy()

    if df.empty:
        result = {
            "edges": [],
            "start_activities": {},
            "end_activities": {},
        }
        context.cache[cache_key] = result
        return result

    df["case:concept:name"] = df["wallet_address"]
    df["concept:name"] = df["action"]
    df["time:timestamp"] = pd.to_datetime(
        df["event_time"],
        utc=True,
    )

    df = df.sort_values(
        ["case:concept:name", "time:timestamp"],
        kind="stable",
    )

    # Discover the DFG directly. Do NOT call discover_dfg(),
    # because that function also exports images and JSON files.
    dfg, start_activities, end_activities = pm4py.discover_dfg(
        df,
        case_id_key="case:concept:name",
        activity_key="concept:name",
        timestamp_key="time:timestamp",
    )

    result = {
        "edges": [
            {
                "source": source,
                "target": target,
                "count": int(count),
            }
            for (source, target), count in dfg.items()
        ],
        "start_activities": {
            str(activity): int(count)
            for activity, count in start_activities.items()
        },
        "end_activities": {
            str(activity): int(count)
            for activity, count in end_activities.items()
        },
    }

    context.cache[cache_key] = result
    return result


def build_filtered_dfg_tools(context: AnalysisContext):
    @tool
    def get_filtered_dfg(
        min_edge_count: int = 1,
        include_probabilities: bool = True,
    ) -> dict[str, Any]:
        """Analyze the filtered Directly-Follows Graph of wallet actions.

        Use this tool to investigate common action transitions, their
        frequencies, and optionally their conditional transition probabilities.

        min_edge_count: Minimum edge frequency to retain.
        include_probabilities: Whether to calculate transition probabilities.

        Returns filtered edges, start and end activities, and statistics.
        """

        if min_edge_count < 1:
            return {
                "error": "min_edge_count must be at least 1."
            }

        raw_dfg = _discover_raw_dfg(context)

        filtered_edges = [
            edge
            for edge in raw_dfg["edges"]
            if (
                edge["count"] >= min_edge_count
                and edge["source"] not in EXCLUDED_ACTIVITIES
                and edge["target"] not in EXCLUDED_ACTIVITIES
            )
        ]

        visible_activities = {
            activity
            for edge in filtered_edges
            for activity in (edge["source"], edge["target"])
        }

        filtered_dfg = {
            "edges": filtered_edges,
            "start_activities": {
                activity: count
                for activity, count in raw_dfg["start_activities"].items()
                if activity in visible_activities
            },
            "end_activities": {
                activity: count
                for activity, count in raw_dfg["end_activities"].items()
                if activity in visible_activities
            },
        }

        if include_probabilities and filtered_edges:
            filtered_dfg = add_transition_probabilities(filtered_dfg)

        return {
            **filtered_dfg,
            "statistics": {
                "original_edge_count": len(raw_dfg["edges"]),
                "filtered_edge_count": len(filtered_edges),
                "min_edge_count": min_edge_count,
                "excluded_activities": sorted(EXCLUDED_ACTIVITIES),
            },
        }

    return [get_filtered_dfg]
