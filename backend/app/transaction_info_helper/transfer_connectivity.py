
from collections import deque
from typing import Any


def check_transfer_connectivity(
    wallet_transfers: dict[str, dict[str, list[dict[str, Any]]]],
    source_wallet: str,
    target_wallet: str,
    target_token_mint: str,
) -> dict[str, Any]:
    """
    Find the shortest path between two wallets using transfer relationships.

    Transfers are treated as undirected edges for connectivity analysis.
    Token type does not restrict traversal.
    """

    if source_wallet == target_wallet:
        return {
            "connected": True,
            "path_length": 0,
            "wallets": [source_wallet],
            "target_mint_involved": False,
            "native_token_involved": False,
            "path_transfers": [],
        }

    # Build undirected adjacency from all transfers.
    adjacency: dict[str, set[str]] = {}
    transfers_by_pair: dict[
        frozenset[str], list[dict[str, Any]]
    ] = {}

    for wallet, directions in wallet_transfers.items():
        for direction in ("incoming", "outgoing"):
            for transfer in directions[direction]:
                sender = transfer.get("from_wallet")
                receiver = transfer.get("to_wallet")

                if not sender or not receiver or sender == receiver:
                    continue

                adjacency.setdefault(sender, set()).add(receiver)
                adjacency.setdefault(receiver, set()).add(sender)

                pair = frozenset((sender, receiver))
                transfers_by_pair.setdefault(pair, []).append(transfer)

    # BFS: find the shortest path in number of transfer hops.
    queue = deque([source_wallet])
    parent: dict[str, str | None] = {source_wallet: None}

    while queue:
        current = queue.popleft()

        if current == target_wallet:
            break

        for neighbor in adjacency.get(current, set()):
            if neighbor in parent:
                continue

            parent[neighbor] = current
            queue.append(neighbor)

    if target_wallet not in parent:
        return {
            "connected": False,
            "path_length": None,
            "wallets": [],
            "target_mint_involved": False,
            "native_token_involved": False,
            "path_transfers": [],
        }

    # Reconstruct the path from target to source.
    path = []
    current: str | None = target_wallet

    while current is not None:
        path.append(current)
        current = parent[current]

    path.reverse()

    # Collect transfer records associated with each path edge.
    path_transfers = []

    for index in range(len(path) - 1):
        pair = frozenset((path[index], path[index + 1]))

        path_transfers.append({
            "from_wallet": path[index],
            "to_wallet": path[index + 1],
            "transfers": transfers_by_pair[pair],
        })

    # Check whether any transfer on the path involves the target mint
    # or native SOL (represented by mint=None).
    target_mint_involved = False
    native_token_involved = False

    for edge in path_transfers:
        for transfer in edge["transfers"]:
            mint = transfer.get("mint")

            if mint == target_token_mint:
                target_mint_involved = True

            if mint is None:
                native_token_involved = True

    return {
        "connected": True,
        "path_length": len(path) - 1,
        "wallets": path,
        "target_mint_involved": target_mint_involved,
        "native_token_involved": native_token_involved,
        #"path_transfers": path_transfers,
    }
