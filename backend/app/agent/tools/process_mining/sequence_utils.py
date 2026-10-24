
def collapse_sequence(sequence: list[str]) -> list[dict]:
    """Collapse consecutive identical actions while preserving counts."""

    if not sequence:
        return []

    result = []
    current_action = sequence[0]
    count = 1

    for action in sequence[1:]:
        if action == current_action:
            count += 1
        else:
            result.append({
                "action": current_action,
                "count": count,
            })
            current_action = action
            count = 1

    result.append({
        "action": current_action,
        "count": count,
    })

    return result
