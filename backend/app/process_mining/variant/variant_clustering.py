
from rapidfuzz.distance import Levenshtein


def cluster_variants(
    variants: list[dict],
    max_length_diff: int = 2,
    max_distance_ratio: float = 0.1,
) -> dict:
    # Each unique variant is represented only once.
    items = [
        {
            "id": v["variant_id"],
            "sequence": v["sequence"],
            "wallets": v["wallets"],
        }
        for v in variants
    ]

    parent = {item["id"]: item["id"] for item in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    # Compare each unordered pair once.
    for i, a in enumerate(items):
        seq_a = a["sequence"]

        for b in items[i + 1:]:
            seq_b = b["sequence"]

            # Avoid expensive comparisons between very different lengths.
            if abs(len(seq_a) - len(seq_b)) > max_length_diff:
                continue

            distance = Levenshtein.distance(seq_a, seq_b)
            denominator = max(len(seq_a), len(seq_b), 1)
            ratio = distance / denominator

            if ratio <= max_distance_ratio:
                union(a["id"], b["id"])

    groups = {}

    for item in items:
        root = find(item["id"])
        groups.setdefault(root, []).append(item)

    clusters = []
    unclustered = []

    for group in groups.values():
        if len(group) < 2:
            unclustered.append(group[0]["id"])
            continue

        wallets = sorted({
            wallet
            for item in group
            for wallet in item["wallets"]
        })

        clusters.append({
            "cluster_id": f"C{len(clusters) + 1}",
            "variant_ids": [item["id"] for item in group],
            "wallet_count": len(wallets),
            "wallets": wallets,
        })

    return {
        "clusters": clusters,
        "unclustered_variant_ids": unclustered,
    }
