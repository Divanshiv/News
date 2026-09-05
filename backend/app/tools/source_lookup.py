"""Source registry lookup/creation for research-discovered references."""

import logging
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source

logger = logging.getLogger(__name__)

DISCOVERED_RELIABILITY = 0.3

_TIER_DOMAIN_HINTS = {
    "primary": (
        ".gov",
        ".gov.in",
        ".mil",
        ".edu",
        "europa.eu",
        "un.org",
        "who.int",
        "nasa.gov",
        "isro.gov.in",
        "github.com",
        "arxiv.org",
    ),
    "social": ("twitter.com", "x.com", "reddit.com", "youtube.com", "t.me"),
}


def domain_of(url: str) -> str:
    return (urlparse(url).netloc or "").lower().replace("www.", "")


def tier_for_url(url: str, source_type: str | None = None) -> str:
    if source_type in {"official", "government", "research"}:
        return "primary"
    host = domain_of(url)
    lowered = f"{host} {host.rsplit('.', 1)[-1] if host else ''}".lower()
    if any(hint in lowered for hint in _TIER_DOMAIN_HINTS["primary"]):
        return "primary"
    if any(hint in lowered for hint in _TIER_DOMAIN_HINTS["social"]):
        return "social"
    return "news"


def normalize_research_url(url: str) -> str:
    parsed = urlparse(url)
    parsed = parsed._replace(fragment="")
    query_pairs = [
        (k, v)
        for k, v in (p.split("=", 1) for p in parsed.query.split("&") if p)
        if k.lower()
        not in {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "fbclid",
            "gclid",
        }
    ]
    order = sorted(query_pairs, key=lambda kv: (kv[0], kv[1]))
    return parsed._replace(query="&".join(f"{k}={v}" for k, v in order)).geturl()


class SourceLookupTool:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    def bind(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_url(self, url: str) -> Source | None:
        if self._session is None:
            return None
        normalized = normalize_research_url(url)
        domain = domain_of(url)
        result = await self._session.execute(
            select(Source).where(
                (Source.url == normalized) | (Source.url == url) | (Source.rss_url == url)
            )
        )
        by_url = result.scalars().first()
        if by_url is not None:
            return by_url
        result = await self._session.execute(
            select(Source).where(Source.url.ilike(f"%{domain}%"))
        )
        return result.scalars().first()

    async def get_or_create(
        self,
        *,
        url: str,
        name: str | None = None,
        category: str | None = None,
        source_type: str = "news",
    ) -> Source | None:
        if self._session is None:
            return None
        existing = await self.find_by_url(url)
        if existing is not None:
            return existing
        domain = domain_of(url)
        source = Source(
            name=(name or domain)[:200],
            url=normalize_research_url(url)[:500],
            source_type=source_type,
            category=category,
            reliability_score=DISCOVERED_RELIABILITY,
            license_notes="Discovered during research; verify terms before reuse.",
            active=True,
        )
        try:
            self._session.add(source)
            await self._session.flush()
            return source
        except Exception:
            logger.warning("failed to create research source for %s", url, exc_info=True)
            await self._session.rollback()
            return None