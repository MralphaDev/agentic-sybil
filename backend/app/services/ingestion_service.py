
import time
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import UploadFile

from app.api.providers.helius.client import HeliusClient
from app.api.providers.solana_rpc.client import SolanaRpcClient
from app.api_normalization.normalization import normalize_transaction
from app.ingestion.forensic.cleaner import clean_csv
from app.database.queries import (
    save_wallet_event,
    save_wallet_holdings,
    get_wallet_profiles,
    upsert_wallet_profile,
)


def timed_step(name: str, func: Callable, *args, **kwargs) -> Any:
    """Time a synchronous operation."""
    start = time.perf_counter()
    try:
        return func(*args, **kwargs)
    finally:
        print(
            f"[TIMING] {name}: {time.perf_counter() - start:.4f}s",
            flush=True,
        )


async def timed_async_step(
    name: str,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """Time an asynchronous operation."""
    start = time.perf_counter()
    try:
        return await func(*args, **kwargs)
    finally:
        print(
            f"[TIMING] {name}: {time.perf_counter() - start:.4f}s",
            flush=True,
        )


async def ingest_forensic_csv(
    file: UploadFile,
    token_address: str,
) -> dict:
    """Ingest a forensic CSV and collect wallet transaction and holding data."""

    total_start = time.perf_counter()

    try:
        # 1. Validate target token address.
        timed_step(
            "validate_token_address",
            lambda: None
            if token_address and token_address.strip()
            else (_ for _ in ()).throw(
                ValueError("token_address must not be empty")
            ),
        )
        token_address = token_address.strip()

        # 2. Read and clean CSV.
        content = await timed_async_step(
            "read_csv_upload",
            file.read,
        )

        rows = timed_step("clean_csv", clean_csv, content)

        print(f"[INGESTION] CSV rows: {len(rows)}", flush=True)

        results = []
        skipped_addresses = []

        # 3. Batch-read all existing profiles in ONE database query.
        addresses = list(dict.fromkeys(
            row["address"] for row in rows
        ))

        profiles = timed_step(
            "get_wallet_profiles_batch",
            get_wallet_profiles,
            addresses,
        )

        profiles_by_address = {
            profile["wallet_address"]: profile
            for profile in profiles
        }

        print(
            f"[INGESTION] Batch-loaded {len(profiles_by_address)} "
            f"profiles for {len(addresses)} unique addresses",
            flush=True,
        )

        # 4. Process each wallet individually.
        async with HeliusClient() as helius, SolanaRpcClient() as solana:
            for index, row in enumerate(rows, start=1):
                address = row["address"]
                wallet_start = time.perf_counter()
                prefix = f"wallet[{index}/{len(rows)}]"

                # Initialize before try so failure handling is safe.
                is_contract = row.get("is_contract") is True
                is_exchange = row.get("is_exchange") is True

                print(
                    f"[INGESTION] Processing {prefix}: {address}",
                    flush=True,
                )

                try:
                    # 5. Read profile from memory, not the database.
                    profile = profiles_by_address.get(address)

                    if profile and profile["forensic_status"] == "completed":
                        skipped_addresses.append(address)

                        print(
                            f"[INGESTION] Skipped completed wallet: {address}",
                            flush=True,
                        )
                        continue

                    # 6. Mark profile as processing.
                    timed_step(
                        f"{prefix}.upsert_profile_processing",
                        upsert_wallet_profile,
                        wallet_address=address,
                        is_contract=is_contract,
                        is_exchange=is_exchange,
                        forensic_status="processing",
                    )

                    transactions = []
                    raw_transactions = []
                    holdings = []

                    # 7. Fetch transaction history.
                    if not is_contract and not is_exchange:
                        oldest_transactions = await timed_async_step(
                            f"{prefix}.helius_oldest_transactions",
                            helius.get_transactions_for_address,
                            address=address,
                            limit=100,
                            sort_order="asc",
                        )

                        newest_transactions = await timed_async_step(
                            f"{prefix}.helius_newest_transactions",
                            helius.get_transactions_for_address,
                            address=address,
                            limit=100,
                            sort_order="desc",
                        )

                        # 8. Deduplicate transactions by signature.
                        def deduplicate_transactions():
                            unique = {}

                            for tx in oldest_transactions + newest_transactions:
                                signature = tx.get("signature")
                                if signature:
                                    unique[signature] = tx

                            return list(unique.values())

                        raw_transactions = timed_step(
                            f"{prefix}.deduplicate_transactions",
                            deduplicate_transactions,
                        )

                        # 9. Sort transactions oldest -> newest.
                        timed_step(
                            f"{prefix}.sort_transactions",
                            raw_transactions.sort,
                            key=lambda tx: (
                                (tx.get("parsed") or {}).get("blockTime") is None,
                                (tx.get("parsed") or {}).get("blockTime") or 0,
                                tx.get("signature") or "",
                            ),
                        )

                        # 10. Normalize and persist events individually.
                        for tx_index, item in enumerate(
                            raw_transactions,
                            start=1,
                        ):
                            normalized = timed_step(
                                f"{prefix}.normalize_tx[{tx_index}]",
                                normalize_transaction,
                                item=item,
                                address=address,
                            )

                            if normalized is not None:
                                timed_step(
                                    f"{prefix}.save_wallet_event[{tx_index}]",
                                    save_wallet_event,
                                    wallet_address=address,
                                    result=normalized,
                                )
                                transactions.append(normalized)

                        print(
                            f"[INGESTION] {address}: "
                            f"{len(raw_transactions)} fetched, "
                            f"{len(transactions)} normalized",
                            flush=True,
                        )

                        # 11. Calculate observed wallet features.
                        def calculate_first_active_time():
                            block_times = [
                                int((tx.get("parsed") or {})["blockTime"])
                                for tx in raw_transactions
                                if (tx.get("parsed") or {}).get("blockTime")
                                is not None
                            ]

                            if not block_times:
                                return None

                            return datetime.fromtimestamp(
                                min(block_times),
                                tz=timezone.utc,
                            )

                        first_active_time = timed_step(
                            f"{prefix}.calculate_first_active_time",
                            calculate_first_active_time,
                        )

                        # First observed funding is not necessarily first activity.
                        first_fund_time = None
                        first_fund_amount = 0
                        first_fund_token = None

                        # This is the number fetched, not lifetime transaction count.
                        total_tx_count = len(raw_transactions)

                    else:
                        first_active_time = None
                        first_fund_time = None
                        first_fund_amount = 0
                        first_fund_token = None
                        total_tx_count = 0

                    # 12. Fetch and persist token holdings.
                    try:
                        holdings = await timed_async_step(
                            f"{prefix}.solana_get_token_holdings",
                            solana.get_token_holdings,
                            address,
                        )

                        timed_step(
                            f"{prefix}.save_wallet_holdings",
                            save_wallet_holdings,
                            address,
                            holdings,
                        )

                    except RuntimeError as exc:
                        if "-32603" in str(exc):
                            print(
                                f"[Forensic] Skipping holdings for {address}: "
                                "Solana RPC internal error.",
                                flush=True,
                            )
                        else:
                            raise

                    # 13. Mark profile completed.
                    timed_step(
                        f"{prefix}.upsert_profile_completed",
                        upsert_wallet_profile,
                        wallet_address=address,
                        is_contract=is_contract,
                        is_exchange=is_exchange,
                        forensic_status="completed",
                        first_active_time=first_active_time,
                        first_fund_time=first_fund_time,
                        first_fund_amount=first_fund_amount,
                        first_fund_token=first_fund_token,
                        total_tx_count=total_tx_count,
                        processed_at=datetime.now(timezone.utc),
                    )

                    results.append({
                        "address": address,
                        "transactions": transactions,
                        "transactions_fetched": len(raw_transactions),
                        "token_holdings": holdings,
                    })

                except Exception:
                    # Preserve original retry behavior.
                    timed_step(
                        f"{prefix}.upsert_profile_failed",
                        upsert_wallet_profile,
                        wallet_address=address,
                        is_contract=is_contract,
                        is_exchange=is_exchange,
                        forensic_status="failed",
                    )
                    raise

                finally:
                    print(
                        f"[TIMING] {prefix}.TOTAL: "
                        f"{time.perf_counter() - wallet_start:.4f}s",
                        flush=True,
                    )

        return {
            "filename": file.filename,
            "token_address": token_address,
            "addresses_processed": len(results),
            "addresses_skipped": len(skipped_addresses),
            "skipped_addresses": skipped_addresses,
            "data": results,
        }

    finally:
        print(
            f"[TIMING] ingest_forensic_csv TOTAL: "
            f"{time.perf_counter() - total_start:.4f}s",
            flush=True,
        )


async def ingest_realtime_address(
    address: str,
    limit: int = 100,
) -> dict:
    """Fetch and ingest on-chain activity for an address."""

    # TODO: Fetch data through Helius client.
    # TODO: Normalize events.
    # TODO: Persist events.

    raise NotImplementedError
