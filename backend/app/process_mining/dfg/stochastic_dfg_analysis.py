
from collections import defaultdict


def add_transition_probabilities(
    dfg: dict,
    decimal_places: int = 6,
) -> dict:
    """
    Convert a regular DFG into a stochastic DFG.

    Easy explanation:
        A regular DFG tells us how many times each edge appears.
        A stochastic DFG additionally tells us the probability
        of following each edge, given its source activity.

    Example:
        receive -> transfer: 80 times
        receive -> swap:     20 times

        P(transfer | receive) = 80 / (80 + 20) = 0.8
        P(swap | receive)     = 20 / (80 + 20) = 0.2

    Expected input:
        {
            "edges": [
                {
                    "source": "receive",
                    "target": "transfer",
                    "count": 80,
                },
                ...
            ],
            "start_activities": {...},
            "end_activities": {...},
        }

    Returns:
        The same DFG structure, with additional information
        attached to every edge.

    Important:
        These probabilities describe observed event transitions.
        They are not probabilities that a wallet is a Sybil wallet.
    """
    if decimal_places < 0:
        raise ValueError("decimal_places cannot be negative.")

    edges = dfg.get("edges", [])

    # Step 1:
    # Count all outgoing transitions from each source activity.
    #
    # For example:
    # receive -> transfer: 80
    # receive -> swap:     20
    #
    # outgoing_totals["receive"] = 100
    outgoing_totals: defaultdict[str, int | float] = defaultdict(int)

    for edge in edges:
        source = edge["source"]
        count = edge["count"]

        if not isinstance(count, (int, float)) or count < 0:
            raise ValueError(
                f"Invalid edge count for {source}: {count}"
            )

        outgoing_totals[source] += count

    # Step 2:
    # Calculate each edge's conditional transition probability.
    stochastic_edges = []

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        count = edge["count"]

        total_outgoing = outgoing_totals[source]

        # P(next activity = target | current activity = source)
        probability = (
            count / total_outgoing
            if total_outgoing > 0
            else 0.0
        )

        # Keep all original edge fields and add probability fields.
        stochastic_edge = {
            **edge,
            "outgoing_transition_count": total_outgoing,
            "transition_probability": round(
                probability,
                decimal_places,
            ),
        }

        stochastic_edges.append(stochastic_edge)

    # Step 3:
    # Return a new DFG object.
    # The original DFG is not modified.
    return {
        **dfg,
        "edges": stochastic_edges,
        "type": "stochastic_dfg",
        "probability_definition": (
            "P(target | source) = edge count / "
            "total outgoing edge count from source"
        ),
    }
