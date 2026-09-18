"""HTTP fetching for research URLs with bounded retries and timeouts."""

import asyncio
import logging
import re

import httpx

from ._browser_headers import BROWSER_HEADERS

logger = logging.getLogger(__name__)

_META_CHARSET_RE = re.compile(
    br'<meta[^>]+charset=["\']?\s*([A-Za-z0-9._-]+)', re.IGNORECASE
)
_META_HTTP_EQUIV_RE = re.compile(
    br'<meta[^>]+content=["\'][^"\']*charset=([A-Za-z0-9._-]+)', re.IGNORECASE
)


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
                return self._decode(response)
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(self._backoff * 2 ** (attempts - 1))
        raise URLFetchError(f"failed to fetch {url}: {last_error}")

    def _decode(self, response: httpx.Response) -> str:
        content = response.content[: self._max_bytes]
        charset = self._header_charset(response)
        if charset:
            try:
                return content.decode(charset)
            except (LookupError, UnicodeDecodeError):
                pass
        declared = self._meta_charset(content)
        if declared:
            try:
                return content.decode(declared)
            except (LookupError, UnicodeDecodeError):
                pass
        best = self._sniff_charset(content)
        if best:
            return best
        return content.decode("utf-8", errors="replace")

    @staticmethod
    def _header_charset(response: httpx.Response) -> str:
        content_type = response.headers.get("content-type", "")
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                return part.split("=", 1)[1].strip().strip('"')
        return ""

    @staticmethod
    def _meta_charset(content: bytes) -> str:
        match = _META_HTTP_EQUIV_RE.search(content) or _META_CHARSET_RE.search(content)
        if match:
            try:
                return match.group(1).decode("ascii").strip("'\"")
            except UnicodeDecodeError:
                return ""
        return ""

    @staticmethod
    def _sniff_charset(content: bytes) -> str:
        from charset_normalizer import from_bytes

        best = from_bytes(content).best()
        if best is not None:
            return str(best)
        return ""

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()