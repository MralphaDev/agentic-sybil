import asyncio
import random
from decimal import Decimal
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import httpx


class SolanaRpcClient:
    RPC_URL = "https://api.mainnet-beta.solana.com"

    TOKEN_PROGRAMS = {
        "SPL Token": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "Token-2022": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    }

    # Conservative local rate limit: approximately 3 requests/sec.
    REQUESTS_PER_SECOND = 3

    MAX_ATTEMPTS = 5
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 30.0

    RETRYABLE_STATUS_CODES = {
        408,
        429,
        500,
        502,
        503,
        504,
    }

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._http_client = http_client
        self._owns_client = http_client is None

        self._request_lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._min_request_interval = 1.0 / self.REQUESTS_PER_SECOND

    async def __aenter__(self):
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.RPC_URL,
                timeout=httpx.Timeout(30.0),
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _wait_for_rate_limit(self) -> None:
        """Space requests from this client instance."""
        async with self._request_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()

            wait_time = (
                self._min_request_interval
                - (now - self._last_request_time)
            )

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            self._last_request_time = loop.time()

    @staticmethod
    def _get_retry_after(response: httpx.Response) -> float | None:
        """Parse Retry-After as seconds or an HTTP date."""
        value = response.headers.get("Retry-After")

        if not value:
            return None

        try:
            # Retry-After: 5
            return max(0.0, float(value))
        except ValueError:
            pass

        try:
            # Retry-After: Wed, 21 Oct 2026 07:28:00 GMT
            retry_time = parsedate_to_datetime(value)

            if retry_time.tzinfo is None:
                retry_time = retry_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            return max(0.0, (retry_time - now).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None

    def _get_backoff(self, attempt: int) -> float:
        """Exponential backoff with a small random spread."""
        delay = min(
            self.INITIAL_BACKOFF * (2 ** (attempt - 1)),
            self.MAX_BACKOFF,
        )
        return delay + random.uniform(0, min(1.0, delay * 0.1))

    async def _rpc_call(
        self,
        method: str,
        params: list,
    ) -> dict:
        """Execute an RPC request with rate limiting and retries."""
        if self._http_client is None:
            raise RuntimeError(
                "Use SolanaRpcClient with 'async with'."
            )

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            await self._wait_for_rate_limit()

            try:
                response = await self._http_client.post(
                    "",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params,
                    },
                )

                # Handle HTTP errors before parsing the JSON body.
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if response.status_code == 429:
                        print("[Solana RPC] Rate limited!")
                        print(
                            "Retry-After:",
                            response.headers.get("Retry-After"),
                        )
                        print(
                            "Response body:",
                            response.text[:1000],
                        )

                    if attempt == self.MAX_ATTEMPTS:
                        response.raise_for_status()

                    retry_after = (
                        self._get_retry_after(response)
                        if response.status_code == 429
                        else None
                    )

                    delay = (
                        retry_after
                        if retry_after is not None
                        else self._get_backoff(attempt)
                    )

                    print(
                        f"[Solana RPC] HTTP {response.status_code}. "
                        f"Attempt {attempt}/{self.MAX_ATTEMPTS}. "
                        f"Retrying in {delay:.1f}s."
                    )

                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                body = response.json()

                if "error" in body:
                    error = body["error"]
                    code = error.get("code")

                    # Retry transient RPC server errors.
                    if code in (-32005, -32603) and attempt < self.MAX_ATTEMPTS:
                        delay = self._get_backoff(attempt)

                        print(
                            f"[Solana RPC] RPC error {code}: "
                            f"{error.get('message', 'Unknown error')}. "
                            f"Attempt {attempt}/{self.MAX_ATTEMPTS}. "
                            f"Retrying in {delay:.1f}s."
                        )

                        await asyncio.sleep(delay)
                        continue

                    raise RuntimeError(
                        f"Solana RPC error: {error}"
                    )

                return body["result"]

            except (
                httpx.TimeoutException,
                httpx.TransportError,
            ) as exc:
                if attempt == self.MAX_ATTEMPTS:
                    raise

                delay = self._get_backoff(attempt)

                print(
                    f"[Solana RPC] Network error: "
                    f"{type(exc).__name__}. "
                    f"Attempt {attempt}/{self.MAX_ATTEMPTS}. "
                    f"Retrying in {delay:.1f}s."
                )

                await asyncio.sleep(delay)

        raise RuntimeError(
            "Solana RPC request failed after all attempts."
        )

    async def get_token_holdings(
        self,
        address: str,
    ) -> list[dict]:
        """Fetch token balances for SPL Token and Token-2022."""
        totals = {}

        for program_name, program_id in self.TOKEN_PROGRAMS.items():
            result = await self._rpc_call(
                "getTokenAccountsByOwner",
                [
                    address,
                    {"programId": program_id},
                    {"encoding": "jsonParsed"},
                ],
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
            if entry["raw_amount"] <= 0:
                continue

            amount = (
                Decimal(entry["raw_amount"])
                / (Decimal(10) ** entry["decimals"])
            )

            holdings.append(
                {
                    "mint": entry["mint"],
                    "amount": str(amount),
                    "decimals": entry["decimals"],
                    "program": ", ".join(
                        sorted(entry["programs"])
                    ),
                }
            )

        # Sort by token quantity, not USD value.
        holdings.sort(
            key=lambda token: Decimal(token["amount"]),
            reverse=True,
        )

        return holdings[:5]