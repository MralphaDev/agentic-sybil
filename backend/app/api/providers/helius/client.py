
import asyncio

import httpx

from app.core.config import settings


BASE_URL = "https://mainnet.helius-rpc.com/"
HISTORY_URL = "https://api.helius.xyz/v1/parsed-events/transaction-history"


class HeliusClient:
    # Rate limiting
    REQUESTS_PER_SECOND = 10

    # Retry policy
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
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = settings.HELIUS_API_KEY

        self._client = client
        self._owns_client = client is None

        # Share the rate limiter across both endpoints
        # within this client instance.
        self._request_lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._min_request_interval = (
            1.0 / self.REQUESTS_PER_SECOND
        )

    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        if self._owns_client and self._client is not None:
            await self._client.aclose()

        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
            self._owns_client = True

        return self._client

    async def _wait_for_rate_limit(self) -> None:
        """Space requests at approximately 10 requests per second."""
        async with self._request_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()

            elapsed = now - self._last_request_time
            wait_time = self._min_request_interval - elapsed

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            self._last_request_time = loop.time()

    async def _post_with_retry(
        self,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """POST with rate limiting and exponential backoff."""
        client = await self._get_client()

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            await self._wait_for_rate_limit()

            try:
                response = await client.post(
                    url,
                    params=params,
                    json=json,
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt == self.MAX_ATTEMPTS:
                        response.raise_for_status()

                    delay = min(
                        self.INITIAL_BACKOFF * (2 ** (attempt - 1)),
                        self.MAX_BACKOFF,
                    )

                    print(
                        f"[Helius] HTTP {response.status_code}. "
                        f"Attempt {attempt}/{self.MAX_ATTEMPTS}. "
                        f"Retrying in {delay:.0f}s."
                    )

                    await asyncio.sleep(delay)
                    continue

                # Non-retryable HTTP errors are raised immediately.
                response.raise_for_status()

                return response.json()

            except (
                httpx.TimeoutException,
                httpx.TransportError,
            ) as exc:
                if attempt == self.MAX_ATTEMPTS:
                    raise

                delay = min(
                    self.INITIAL_BACKOFF * (2 ** (attempt - 1)),
                    self.MAX_BACKOFF,
                )

                print(
                    f"[Helius] Network error: {type(exc).__name__}. "
                    f"Attempt {attempt}/{self.MAX_ATTEMPTS}. "
                    f"Retrying in {delay:.0f}s."
                )

                await asyncio.sleep(delay)

        raise RuntimeError(
            "Helius request failed after all attempts."
        )

    async def get_transactions_for_address(
        self,
        address: str,
        limit: int = 100,
        sort_order: str = "asc",
    ) -> list[dict]:
        """
        Fetch parsed transaction history.

        sort_order:
            'asc'  -> oldest first
            'desc' -> newest first
        """
        if sort_order not in {"asc", "desc"}:
            raise ValueError(
                "sort_order must be 'asc' or 'desc'."
            )

        if not 1 <= limit <= 100:
            raise ValueError(
                "limit must be between 1 and 100."
            )

        data = await self._post_with_retry(
            HISTORY_URL,
            params={"api-key": self.api_key},
            json={
                "address": address,
                "limit": limit,
                "sortOrder": sort_order,
                "commitment": "confirmed",
                "includeRawTransaction": False,
            },
        )

        transactions = data.get("data", [])

        if not isinstance(transactions, list):
            raise ValueError(
                "Unexpected Helius transaction-history response: "
                "'data' is not a list."
            )

        return transactions

    async def get_transfers_for_address(
        self,
        address: str,
        limit: int = 20,
    ) -> list[dict]:
        """Fetch transfers for an address using Helius RPC."""
        if not 1 <= limit <= 100:
            raise ValueError(
                "limit must be between 1 and 100."
            )

        data = await self._post_with_retry(
            BASE_URL,
            params={"api-key": self.api_key},
            json={
                "jsonrpc": "2.0",
                "id": "agentic-sybil",
                "method": "getTransfersByAddress",
                "params": [
                    address,
                    {"limit": limit},
                ],
            },
        )

        if "error" in data:
            raise RuntimeError(
                f"Helius RPC error: {data['error']}"
            )

        result = data.get("result") or {}
        transfers = result.get("data", [])

        if not isinstance(transfers, list):
            raise ValueError(
                "Unexpected Helius transfer response: "
                "'result.data' is not a list."
            )

        return transfers
