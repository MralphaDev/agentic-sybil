import pandas as pd


COORDINATED_PATTERNS = {
    "native": (
        "receive_native",
        "transfer_native",
    ),
    "target_token": (
        "receive_target_token",
        "transfer_target_token",
    ),
}


def get_coordinated_intermediary(
    df: pd.DataFrame,
    max_gap_minutes: float = 5,
    wallet_col: str = "wallet_address",
    action_col: str = "action",
    time_col: str = "event_time",
) -> dict:
    """
    Identify wallets with consecutive receive -> transfer
    actions within a specified time threshold.

    Supported patterns:
        receive_native -> transfer_native
        receive_target_token -> transfer_target_token
    """
    if df.empty:
        return {
            "max_gap_minutes": max_gap_minutes,
            "total_coordinated_wallets": 0,
            "wallets": [],
        }

    data = df.copy()
    data[time_col] = pd.to_datetime(data[time_col], utc=True)

    sort_cols = [wallet_col, time_col]
    if "signature" in data.columns:
        sort_cols.append("signature")

    data = data.sort_values(sort_cols, kind="stable")

    max_gap = pd.Timedelta(minutes=max_gap_minutes)
    wallets = {}

    for wallet, group in data.groupby(wallet_col, sort=False):
        actions = group[action_col].tolist()
        timestamps = group[time_col].tolist()

        matches = []

        for i in range(len(actions) - 1):
            for pattern_name, (receive, transfer) in (
                COORDINATED_PATTERNS.items()
            ):
                if (
                    actions[i] != receive
                    or actions[i + 1] != transfer
                ):
                    continue

                gap = timestamps[i + 1] - timestamps[i]

                if pd.Timedelta(0) <= gap <= max_gap:
                    matches.append({
                        "pattern": pattern_name,
                        "receive_action": receive,
                        "transfer_action": transfer,
                        "receive_time": timestamps[i].isoformat(),
                        "transfer_time": timestamps[i + 1].isoformat(),
                        "gap_seconds": round(gap.total_seconds(), 2),
                    })

        if matches:
            wallets[wallet] = matches

    return {
        "max_gap_minutes": max_gap_minutes,
        "total_coordinated_wallets": len(wallets),
        "wallets": [
            {
                "wallet_address": wallet,
                "matched_pairs": pairs,
                "matched_pair_count": len(pairs),
                "pattern_types": sorted({
                    pair["pattern"] for pair in pairs
                }),
            }
            for wallet, pairs in wallets.items()
        ],
    }