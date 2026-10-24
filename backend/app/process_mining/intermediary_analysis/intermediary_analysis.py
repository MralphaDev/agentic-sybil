
import pandas as pd


INTERMEDIARY_PATTERNS = {
    "native": (
        "receive_native",
        "transfer_native",
    ),
    "target_token": (
        "receive_target_token",
        "transfer_target_token",
    ),
}


def get_intermediary(
    df: pd.DataFrame,
    wallet_col: str = "wallet_address",
    action_col: str = "action",
    time_col: str = "event_time",
) -> dict:
    """
    Identify wallets exhibiting intermediary behavior.

    Patterns:
        receive_native -> transfer_native
        receive_target_token -> transfer_target_token

    The two actions must be consecutive within a wallet's
    time-ordered event sequence.
    """
    if df.empty:
        return {
            "total_intermediary_wallets": 0,
            "wallets": [],
        }

    data = df.copy()
    data[time_col] = pd.to_datetime(data[time_col], utc=True)

    sort_cols = [wallet_col, time_col]
    if "signature" in data.columns:
        sort_cols.append("signature")

    data = data.sort_values(sort_cols, kind="stable")

    wallets = {}

    for wallet, group in data.groupby(wallet_col, sort=False):
        actions = group[action_col].tolist()
        timestamps = group[time_col].tolist()

        matched_patterns = []

        for pattern_name, (receive, transfer) in (
            INTERMEDIARY_PATTERNS.items()
        ):
            for i in range(len(actions) - 1):
                if (
                    actions[i] == receive
                    and actions[i + 1] == transfer
                ):
                    matched_patterns.append({
                        "pattern": pattern_name,
                        "receive_action": receive,
                        "transfer_action": transfer,
                        "receive_time": timestamps[i].isoformat(),
                        "transfer_time": timestamps[i + 1].isoformat(),
                    })

        if matched_patterns:
            wallets[wallet] = matched_patterns

    return {
        "total_intermediary_wallets": len(wallets),
        "wallets": [
            {
                "wallet_address": wallet,
                "patterns": patterns,
                "pattern_types": sorted({
                    p["pattern"] for p in patterns
                }),
            }
            for wallet, patterns in wallets.items()
        ],
    }
