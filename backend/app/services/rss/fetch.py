"""HTTP fetching for RSS feeds with bounded retries and timeouts."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = 0.6


class RSSFetchError(Exception):
    """Raised when a feed cannot be retrieved after exhausting retries."""


class RSSFetcher:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        retries: int = DEFAULT_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        backoff: float = DEFAULT_BACKOFF,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        )
        self._owns_client = client is None
        self._retries = retries
        self._backoff = backoff

    async def fetch(self, url: str) -> bytes:
        attempts = 0
        last_error: httpx.HTTPError | None = None
        while attempts <= self._retries:
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(self._backoff * 2 ** (attempts - 1))
        raise RSSFetchError(f"failed to fetch {url}: {last_error}")

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()