
import math
from datetime import datetime
from typing import Any


def tx_similarity(tx_i: int, tx_j: int) -> float:
    if tx_i < 0 or tx_j < 0:
        raise ValueError("Transaction counts cannot be negative.")

    if tx_i == 0 and tx_j == 0:
        return 1.0

    if tx_i == 0 or tx_j == 0:
        return 0.0

    # Linear similarity when both transaction counts are below 10.
    if max(tx_i, tx_j) < 10:
        return 1.0 - abs(tx_i - tx_j) / 10.0

    # Ratio similarity otherwise.
    return min(tx_i, tx_j) / max(tx_i, tx_j)


def amount_similarity(
    amt_i: int | float,
    amt_j: int | float,
    delta: float = 0.002,
) -> float:
    if amt_i < 0 or amt_j < 0:
        raise ValueError("Amounts cannot be negative.")

    if max(amt_i, amt_j) <= delta:
        return 1.0

    if amt_i == 0 or amt_j == 0:
        return 0.0

    return min(amt_i, amt_j) / max(amt_i, amt_j)


def time_similarity(
    t_i: datetime,
    t_j: datetime,
    lambda_: float = 2.2,
) -> float:
    if lambda_ <= 0:
        raise ValueError("lambda_ must be positive.")

    # Do not mix timezone-aware and timezone-naive timestamps.
    if (t_i.utcoffset() is None) != (t_j.utcoffset() is None):
        raise ValueError(
            "Timestamps must have compatible timezone awareness."
        )

    diff_minutes = abs((t_i - t_j).total_seconds()) / 60.0

    if diff_minutes <= 5:
        return 1.0

    return math.exp(-(diff_minutes - 5) / lambda_)


def behavior_vector_sim(
    node_i: dict[str, Any],
    node_j: dict[str, Any],
    weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
) -> float:
    if any(weight < 0 for weight in weights):
        raise ValueError("Weights cannot be negative.")

    if not math.isclose(sum(weights), 1.0):
        raise ValueError("Weights must sum to 1.")

    tx_i = node_i["total_tx_count"]
    tx_j = node_j["total_tx_count"]

    if not isinstance(tx_i, int) or not isinstance(tx_j, int):
        raise TypeError("total_tx_count must be an integer.")

    scores: list[tuple[float, float]] = [
        (
            weights[0],
            tx_similarity(tx_i, tx_j),
        )
    ]

    amt_i = node_i.get("first_fund_amount")
    amt_j = node_j.get("first_fund_amount")

    if amt_i is not None and amt_j is not None:
        if not isinstance(amt_i, (int, float)):
            raise TypeError("first_fund_amount must be numeric or None.")
        if not isinstance(amt_j, (int, float)):
            raise TypeError("first_fund_amount must be numeric or None.")

        scores.append(
            (
                weights[1],
                amount_similarity(amt_i, amt_j),
            )
        )

    time_i = node_i.get("first_fund_time")
    time_j = node_j.get("first_fund_time")

    if time_i is not None and time_j is not None:
        if not isinstance(time_i, datetime):
            raise TypeError("first_fund_time must be datetime or None.")
        if not isinstance(time_j, datetime):
            raise TypeError("first_fund_time must be datetime or None.")

        scores.append(
            (
                weights[2],
                time_similarity(time_i, time_j),
            )
        )

    total_weight = sum(weight for weight, _ in scores)

    if total_weight == 0:
        return 0.0

    score = sum(
        weight * similarity
        for weight, similarity in scores
    ) / total_weight

    return round(min(max(score, 0.0), 1.0), 3)
