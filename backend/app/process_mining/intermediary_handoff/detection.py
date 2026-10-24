from __future__ import annotations

import pandas as pd


def detect_behavioral_intermediaries(
    data: pd.DataFrame,
    target_token_mint: str,
    max_actions_after_receive: int = 2,
) -> set[str]:
    """
    Detect wallets where a target-token receive is followed by a target-token
    transfer within the next N actions in the wallet's COMPLETE action stream.

    Intervening actions may involve another mint, e.g. receive_native.
    The receive and transfer events themselves must match target_token_mint.
    Elapsed time between the two events is not restricted.
    """
    detected: set[str] = set()

    for wallet, group in data.groupby("wallet_address", sort=False):
        group = group.sort_values(
            ["event_time", "signature"],
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)

        actions = group["action"].tolist()
        mints = group["mint"].tolist()

        for i, action in enumerate(actions):
            if action != "receive_target_token":
                continue
            if pd.isna(mints[i]) or mints[i] != target_token_mint:
                continue

            # Check the next N actions, excluding the receive event itself.
            stop = min(len(actions), i + max_actions_after_receive + 1)

            for j in range(i + 1, stop):
                if (
                    actions[j] == "transfer_target_token"
                    and not pd.isna(mints[j])
                    and mints[j] == target_token_mint
                ):
                    detected.add(str(wallet))
                    break

    return detected
