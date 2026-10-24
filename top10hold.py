import requests
from decimal import Decimal

RPC_URL = "https://api.mainnet-beta.solana.com"
WALLET = "44pouozzAqaQArNx8uoXNabTsUY8RT5uATsubbE4zrsv"

TOKEN_PROGRAMS = {
    "SPL Token": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "Token-2022": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
}

def rpc_call(method, params):
    response = requests.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data["result"]

def main():
    # Aggregate token accounts by mint (a wallet can have multiple token accounts
    # for the same mint). Query both the original SPL Token Program and Token-2022.
    totals = {}

    for program_name, program_id in TOKEN_PROGRAMS.items():
        result = rpc_call(
            "getTokenAccountsByOwner",
            [WALLET, {"programId": program_id}, {"encoding": "jsonParsed"}],
        )

        for item in result["value"]:
            info = item["account"]["data"]["parsed"]["info"]
            mint = info["mint"]
            amount_info = info["tokenAmount"]
            raw_amount = int(amount_info["amount"])
            decimals = int(amount_info["decimals"])

            entry = totals.setdefault(
                mint,
                {
                    "mint": mint,
                    "raw_amount": 0,
                    "decimals": decimals,
                    "programs": set(),
                },
            )
            entry["raw_amount"] += raw_amount
            entry["programs"].add(program_name)

    holdings = []
    for entry in totals.values():
        amount = Decimal(entry["raw_amount"]) / (Decimal(10) ** entry["decimals"])
        if entry["raw_amount"] > 0:
            holdings.append({
                "mint": entry["mint"],
                "amount": amount,
                "decimals": entry["decimals"],
                "program": ", ".join(sorted(entry["programs"])),
            })

    # "Top 10" here means highest token-unit balance, not USD value.
    holdings.sort(key=lambda x: x["amount"], reverse=True)
    top10 = holdings[:10]

    print(f"Wallet: {WALLET}")
    print(f"Distinct token mints with positive balances: {len(holdings)}")
    print("\nTop 10 holdings by token quantity (NOT USD value):")
    if not top10:
        print("No positive SPL Token balances found.")
    else:
        for rank, token in enumerate(top10, start=1):
            print(
                f"{rank:>2}. mint={token['mint']} | "
                f"amount={token['amount']:,} | "
                f"decimals={token['decimals']} | "
                f"program={token['program']}"
            )

if __name__ == "__main__":
    main()
