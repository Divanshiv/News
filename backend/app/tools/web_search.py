"""Web-search tools. All implement the WebSearchTool contract so the research
agent is backend-agnostic. DuckDuckGo and Bing are keyless and free; Serper is
a commercial option when an API key is configured. ``WEB_SEARCH_BACKEND``
accepts a comma-separated fallback chain (e.g. ``duckduckgo,bing``).
"""

import abc
import asyncio
import base64
import logging
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from ._browser_headers import BROWSER_HEADERS

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchError(Exception):
    pass


def _describe_error(exc: BaseException) -> str:
    """Human description of a transport/HTTP error including its type.

    httpcore exceptions (ConnectTimeout, ReadTimeout, ...) have EMPTY message
    strings, so ``str(exc)`` alone yields a useless trailing blank.
    """
    message = str(exc).strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


class WebSearchTool(abc.ABC):
    @abc.abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Return ranked results for a query."""

    async def close(self) -> None:
        """Release any owned resources (no-op by default)."""


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._row_title: list[str] = []
        self._row_url: str | None = None
        self._row_snippet: list[str] = []
        self._in_result = False
        self._in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "a" and "result__a" in classes:
            self._in_result = True
            self._row_title = []
            self._row_url = attrs.get("href")
            self._row_snippet = []
        elif tag == "a" and "result__snippet" in classes:
            self._in_snippet = True
            self._row_snippet = []

    def handle_data(self, data):
        if self._in_result:
            self._row_title.append(data)
        elif self._in_snippet:
            self._row_snippet.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._in_result and self._row_url:
            title = "".join(self._row_title).strip()
            if title:
                self.results.append(
                    SearchResult(
                        title=title,
                        url=self._row_url,
                        snippet="".join(self._row_snippet).strip(),
                    )
                )
            self._in_result = False
        elif tag == "a" and self._in_snippet:
            snippet = "".join(self._row_snippet).strip()
            if snippet and self.results:
                self.results[-1] = SearchResult(
                    title=self.results[-1].title,
                    url=self.results[-1].url,
                    snippet=snippet,
                )
            self._in_snippet = False


class DuckDuckGoWebSearch(WebSearchTool):
    """Keyless DuckDuckGo HTML search (free, no API key required)."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
        retries: int = 2,
        backoff: float = 0.6,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=BROWSER_HEADERS
        )
        self._owns_client = client is None
        self._retries = retries
        self._backoff = backoff

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query})
        url = f"https://html.duckduckgo.com/html/?{params}"
        attempts = 0
        last_error: httpx.HTTPError | None = None
        while attempts <= self._retries:
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                parser = _DuckDuckGoParser()
                parser.feed(response.text)
                return parser.results[:limit]
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(self._backoff * 2 ** (attempts - 1))
        raise WebSearchError(
            f"duckduckgo search failed for {query!r}: {_describe_error(last_error)}"
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _resolve_bing_url(href: str) -> str:
    """Extract the real destination from a Bing ``/ck/a`` redirect URL.

    Bing base64-encodes the destination into the ``u`` query param and
    prepends an ``a1`` marker; try the raw value first (defensive), then the
    value with the marker stripped.
    """
    if "bing.com/ck/a" not in href:
        return href
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
    encoded = query.get("u", [None])[0]
    if not encoded:
        return href
    candidates = [encoded, encoded[2:]] if len(encoded) > 2 else [encoded]
    for candidate in candidates:
        try:
            padded = candidate + "=" * (-len(candidate) % 4)
            decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
            if decoded.startswith(("http://", "https://")):
                return decoded
        except (ValueError, UnicodeDecodeError):
            continue
    return href


class _BingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._row_title: list[str] = []
        self._row_url: str | None = None
        self._row_snippet: list[str] = []
        self._in_b_algo = False
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "li" and "b_algo" in classes:
            self._in_b_algo = True
            self._row_title = []
            self._row_url = None
            self._row_snippet = []
        elif tag == "h2" and self._in_b_algo:
            self._in_title = True
            self._row_title = []
        elif tag == "a" and self._in_title and self._row_url is None:
            self._row_url = _resolve_bing_url(attrs.get("href", "")) or None
        elif (
            tag == "p"
            and self._in_b_algo
            and any(
                c == "b_caption" or c.startswith("b_lineclamp") for c in classes
            )
        ):
            self._in_snippet = True
            self._row_snippet = []

    def handle_data(self, data):
        if self._in_title:
            self._row_title.append(data)
        elif self._in_snippet:
            self._row_snippet.append(data)

    def handle_endtag(self, tag):
        if tag == "h2" and self._in_title:
            self._in_title = False
        elif tag == "p" and self._in_snippet:
            self._in_snippet = False
        elif tag == "li" and self._in_b_algo:
            title = "".join(self._row_title).strip()
            if title and self._row_url:
                self.results.append(
                    SearchResult(
                        title=title,
                        url=self._row_url,
                        snippet="".join(self._row_snippet).strip(),
                    )
                )
            self._in_b_algo = False


class BingWebSearch(WebSearchTool):
    """Keyless Bing HTML search (free, no API key required)."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
        retries: int = 2,
        backoff: float = 0.6,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=BROWSER_HEADERS
        )
        self._owns_client = client is None
        self._retries = retries
        self._backoff = backoff

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        params = urllib.parse.urlencode(
            {"q": query, "setlang": "en", "cc": "US", "form": "QBLH"}
        )
        url = f"https://www.bing.com/search?{params}"
        attempts = 0
        last_error: httpx.HTTPError | None = None
        while attempts <= self._retries:
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                parser = _BingParser()
                parser.feed(response.text)
                return parser.results[:limit]
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(self._backoff * 2 ** (attempts - 1))
        raise WebSearchError(
            f"bing search failed for {query!r}: {_describe_error(last_error)}"
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class FallbackWebSearch(WebSearchTool):
    """Try backends in order, returning the first non-empty result set.

    Lets ``WEB_SEARCH_BACKEND=duckduckgo,bing`` ride through outages: if the
    primary backend is unreachable or returns no hits, the next one is tried.
    """

    def __init__(self, backends: list[WebSearchTool]) -> None:
        if not backends:
            raise ValueError("FallbackWebSearch needs at least one backend")
        self._backends = backends

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        failures: list[str] = []
        for backend in self._backends:
            try:
                results = await backend.search(query, limit=limit)
                if results:
                    return results
                failures.append(f"{type(backend).__name__}: no results")
            except WebSearchError as exc:
                failures.append(f"{type(backend).__name__}: {exc}")
        raise WebSearchError(
            f"all web search backends failed for {query!r}: {'; '.join(failures)}"
        )

    async def close(self) -> None:
        for backend in self._backends:
            await backend.close()


class SerperWebSearch(WebSearchTool):
    """Commercial web search via the Serper.dev API (requires an API key)."""

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
        retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            timeout=timeout, headers=BROWSER_HEADERS
        )
        self._owns_client = client is None
        self._retries = retries

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        attempts = 0
        last_error: httpx.HTTPError | None = None
        while attempts <= self._retries:
            try:
                response = await self._client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self._api_key},
                    json={"q": query, "num": limit},
                )
                response.raise_for_status()
                organic = response.json().get("organic", [])
                return [
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                    for item in organic
                ][:limit]
            except httpx.HTTPError as exc:
                attempts += 1
                last_error = exc
                if attempts <= self._retries:
                    await asyncio.sleep(0.5 * 2 ** (attempts - 1))
        raise WebSearchError(
            f"serper search failed for {query!r}: {_describe_error(last_error)}"
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
