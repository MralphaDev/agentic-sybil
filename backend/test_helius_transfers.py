
import asyncio
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("HELIUS_API_KEY")
MINT = "C2omVhcvt3DDY77S2KZzawFJQeETZofgZ4eNWWkXpump"

URL = "https://mainnet.helius-rpc.com/v1/parsed-events/transaction-history"


async def main():
    if not API_KEY:
        raise RuntimeError("HELIUS_API_KEY not found in .env")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            URL,
            params={"api-key": API_KEY},
            json={
                "address": MINT,
                "limit": 1,
                "sortOrder": "asc",
                "commitment": "finalized",
            },
        )

        response.raise_for_status()
        result = response.json()

    if "error" in result:
        raise RuntimeError(f"Helius API error: {result['error']}")

    transactions = result.get("data", [])

    if not transactions:
        print("No transactions found.")
        return

    tx = transactions[0]
    parsed = tx.get("parsed") or {}

    timestamp = parsed.get("blockTime")
    signature = tx.get("signature")

    if timestamp is None:
        raise ValueError("blockTime not found in Helius response")

    human_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"Time:      {human_time}")
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {signature}")


if __name__ == "__main__":
    asyncio.run(main())
