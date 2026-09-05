"""HTTP fetching for research URLs with bounded retries and timeouts."""

import asyncio
import logging

import httpx

from ._browser_headers import BROWSER_HEADERS

logger = logging.getLogger(__name__)


def _describe_error(exc: httpx.HTTPError | None) -> str:
    if exc is None:
        return "unknown error"
    details = str(exc)
    return f"{type(exc).__name__}: {details.strip()}" if details else type(exc).__name__


class URLFetchError(Exception):
    pass


class URLFetchTool:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 20.0,
        retries: int = 2,
        backoff: float = 0.6,
        max_bytes: int = 2_000_000,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        )
        self._owns_client = client is None
        self._retries = retries
        self._backoff = backoff
        self._max_bytes = max_bytes

    async def fetch(self, url: str) -> str:
        attempts = 0
        last_error: httpx.HTTPError | None = None
        while attempts <= self._retries:
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type.lower():
                    logger.info("fetching %s returned non-HTML content", url)
                return response.text[: self._max_bytes]
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(self._backoff * 2 ** (attempts - 1))
        raise URLFetchError(f"failed to fetch {url}: {last_error}")

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()