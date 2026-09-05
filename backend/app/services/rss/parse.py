"""RSS/Atom feed parsing via feedparser into normalized FeedItem records."""

import email.utils
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

import feedparser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(value: str | None) -> str | None:
    if value is None:
        return None
    extractor = _TextExtractor()
    extractor.feed(value)
    text = " ".join("".join(extractor.parts).split())
    return text or None


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(candidate)
        if parsed is not None:
            return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _struct_to_datetime(struct) -> datetime | None:
    try:
        return datetime(*struct[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _extract_author(entry) -> str | None:
    author = entry.get("author")
    if isinstance(author, dict):
        return author.get("name")
    return author


def _extract_image(entry) -> str | None:
    thumbnails = entry.get("media_thumbnail") or []
    if thumbnails:
        url = thumbnails[0].get("url")
        if url:
            return url
    for content in entry.get("media_content") or []:
        if content.get("type", "").startswith("image") or content.get("medium") == "image":
            url = content.get("url")
            if url:
                return url
    for enclosure in entry.get("enclosures") or []:
        if enclosure.get("type", "").startswith("image"):
            url = enclosure.get("url") or enclosure.get("href")
            if url:
                return url
    return None


@dataclass
class FeedItem:
    title: str
    url: str
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None


@dataclass
class ParsedFeed:
    feed_title: str | None
    feed_url: str | None
    items: list[FeedItem]
    malformed: bool
    error: str | None


def parse_feed(xml: bytes, source_url: str) -> ParsedFeed:
    parsed = feedparser.parse(xml, sanitize_html=False)
    parsed = feedparser.parse(xml)
    error = None
    if parsed.bozo and not parsed.entries:
        bozo = getattr(parsed, "bozo_exception", None)
        error = f"{type(bozo).__name__}: {bozo}" if bozo else "malformed feed"
    feed = parsed.feed
    items: list[FeedItem] = []
    for entry in parsed.entries:
        title = entry.get("title")
        link = entry.get("link")
        if not title or not link:
            continue
        absolute = urljoin(source_url, link)
        raw_date = entry.get("published") or entry.get("updated")
        published = _struct_to_datetime(entry.get("published_parsed") or entry.get("updated_parsed"))
        if published is None:
            published = parse_datetime(raw_date)
        items.append(
            FeedItem(
                title=title.strip(),
                url=absolute,
                summary=strip_html(entry.get("summary") or entry.get("description")),
                author=_extract_author(entry),
                published_at=published,
                image_url=_extract_image(entry),
            )
        )
    return ParsedFeed(
        feed_title=getattr(feed, "title", None),
        feed_url=getattr(feed, "link", None),
        items=items,
        malformed=bool(parsed.bozo),
        error=error,
    )