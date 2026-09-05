"""Readable-text extraction from fetched HTML using the stdlib HTML parser."""

import re
from html.parser import HTMLParser

from app.tools.url_fetch import URLFetchError, URLFetchTool

_SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "head"}
_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "li",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "blockquote",
    "tr",
}


class _TextParser(HTMLParser):
    def __init__(self, max_chars: int) -> None:
        super().__init__(convert_charrefs=True)
        self._max_chars = max_chars
        self._parts: list[str] = []
        self._skip_depth = 0
        self._length = 0
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title" and not self.title:
            self._capture_title = True
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._push(" ")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._push(" ")

    def handle_data(self, data):
        if getattr(self, "_capture_title", False):
            self.title = data.strip()
            self._capture_title = False
        if self._skip_depth == 0:
            self._push(data)

    def _push(self, text: str) -> None:
        if self._length >= self._max_chars:
            return
        if not text or not text.strip():
            if self._parts and self._parts[-1].endswith(" "):
                return
            text = " "
        remaining = self._max_chars - self._length
        chunk = (text[:remaining] + " ") if len(text) > remaining - 1 else text
        self._parts.append(chunk)
        self._length += len(chunk) * int(text.strip() != "")


class TextExtractionError(Exception):
    pass


class TextExtractionTool:
    def __init__(
        self,
        *,
        fetcher: URLFetchTool | None = None,
        max_chars: int = 6000,
    ) -> None:
        self._fetcher = fetcher or URLFetchTool()
        self._max_chars = max_chars

    async def extract(self, url: str) -> tuple[str, list[str]]:
        try:
            html = await self._fetcher.fetch(url)
        except URLFetchError as exc:
            raise TextExtractionError(str(exc)) from exc
        parser = _TextParser(max_chars=self._max_chars)
        parser.feed(html)
        text = re.sub(r"\s+", " ", " ".join(parser._parts)).strip()
        paragraphs = [p.strip() for p in text.split("  ") if p.strip()]
        return parser.title, paragraphs

    async def close(self) -> None:
        await self._fetcher.close()