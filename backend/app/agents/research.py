"""ResearchAgent — gathers background and corroborating sources for a story.

The agent is pure orchestration: it takes a story (title/summary/category),
uses injected search + fetch tools to assemble a research package (ranked
sources with snippets + candidate claims), and returns it. Persistence is the
worker's job. The LLM is used for claim extraction with a deterministic
fallback, so research runs anywhere.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from app.services.llm.base import LLMError, LLMProvider
from app.tools import SearchResult, TextExtractionTool, WebSearchTool
from app.tools.source_lookup import tier_for_url

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 1

_IGNORED_DOMAINS = {
    "html.duckduckgo.com",
    "duckduckgo.com",
    "google.com",
    "bing.com",
    "linkedin.com",
    "facebook.com",
}

_QUERY_BOOSTERS = ("official announcement", "press release", "statement")

# OSINT-flavored authoritative domains per category. Used as site-restricted
# fallback queries when generic web search returns thin results.
_OSINT_FALLBACK_SITES: dict[str, tuple[str, ...]] = {
    "Cybersecurity": ("bleepingcomputer.com", "krebsonsecurity.com", "thehackernews.com", "nvd.nist.gov"),
    "Space": ("nasa.gov", "spacenews.com", "isro.gov.in"),
    "Science": ("nature.com", "sciencedaily.com", "science.org"),
    "World": ("reuters.com", "un.org", "reliefweb.int", "hrw.org"),
    "India": ("pib.gov.in", "thehindu.com", "ndtv.com"),
    "Business": ("reuters.com", "bloomberg.com", "ft.com"),
    "Technology": ("theverge.com", "arstechnica.com", "techcrunch.com"),
    "AI": ("openai.com", "deepmind.google", "ainews.com"),
}


@dataclass
class ResearchSource:
    url: str
    title: str
    snippet: str = ""
    tier: str = "news"
    relevance: float = 0.5
    fetched: bool = False

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "tier": self.tier,
            "relevance": self.relevance,
            "fetched": self.fetched,
        }


@dataclass
class ResearchClaim:
    text: str
    source_urls: list[str] = field(default_factory=list)


@dataclass
class ResearchPackage:
    query: str
    summary: str
    sources: list[ResearchSource] = field(default_factory=list)
    claims: list[ResearchClaim] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "summary": self.summary,
            "sources": [source.to_dict() for source in self.sources],
            "claims": [{"text": c.text, "source_urls": c.source_urls} for c in self.claims],
        }


class _ClaimsOutput(BaseModel):
    claims: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=1, max_length=500)


_CLAIMS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
        "summary": {"type": "string"},
    },
    "required": ["claims", "summary"],
}

_SYSTEM_PROMPT = (
    "You are the research agent of an AI newsroom. Given a news story and raw "
    "text from related pages, extract the key factual claims the story depends "
    "on and a one-paragraph research summary. Claims must be statements that "
    "could be verified or contradicted by sources. Do not invent facts. "
    "Return ONLY a JSON object with keys \"claims\" (array of short strings) "
    'and "summary" (one short paragraph).'
)


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("research output must be a JSON object")
    return parsed


def build_queries(*, title: str, summary: str | None, category: str | None) -> list[str]:
    title = title.strip()[:200]
    queries = [title]
    for booster in _QUERY_BOOSTERS:
        queries.append(f"{title} {booster}")
    if category and category not in {"World", "Technology"}:
        queries.append(f"{category}: {title}")
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            unique.append(query)
    return unique


def osint_fallback_queries(*, title: str, category: str | None) -> list[str]:
    sites = _OSINT_FALLBACK_SITES.get(category or "", ())
    title = title.strip()[:200]
    return [f"{title} site:{domain}" for domain in sites[:2]]


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    from app.tools.source_lookup import normalize_research_url

    seen: set[str] = set()
    unique: list[SearchResult] = []
    for result in results:
        normalized = normalize_research_url(result.url)
        domain = normalized.split("//")[-1].split("/")[0].lower()
        if domain in _IGNORED_DOMAINS or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(
            SearchResult(
                title=result.title or normalized,
                url=normalized,
                snippet=result.snippet,
            )
        )
    return unique


def _fallback_claims(text: str) -> tuple[list[str], str]:
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    claims = [s.strip() for s in sentences if 40 <= len(s.strip()) <= 240][:5]
    if not claims:
        claims = [text.strip()[:200]]
    summary = claims[0][:200] + ("…" if len(claims[0]) > 200 else "")
    return claims, summary


class ResearchAgent:
    def __init__(
        self,
        provider: LLMProvider,
        search: WebSearchTool,
        fetch: TextExtractionTool,
        *,
        max_queries: int = 2,
        fetch_limit: int = 4,
        max_sources: int = 6,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._provider = provider
        self._search = search
        self._fetch = fetch
        self._max_queries = max_queries
        self._fetch_limit = fetch_limit
        self._max_sources = max_sources
        self._max_retries = max_retries

    async def research(
        self,
        *,
        title: str,
        summary: str | None = None,
        category: str | None = None,
    ) -> ResearchPackage:
        queries = build_queries(title=title, summary=summary, category=category)
        if self._max_queries > 1 and len(queries) > self._max_queries:
            queries = queries[: self._max_queries]
        all_results: list[SearchResult] = []
        for query in queries:
            try:
                results = await self._search.search(query)
                all_results.extend(results)
            except Exception as exc:
                logger.warning("search failed for query %r: %s", query, exc)
        if len(all_results) < self._max_sources:
            for query in osint_fallback_queries(title=title, category=category):
                try:
                    results = await self._search.search(query)
                    all_results.extend(results)
                except Exception as exc:
                    logger.warning("search failed for query %r: %s", query, exc)
        results = _dedupe_results(all_results)[: self._max_sources]

        sources: list[ResearchSource] = []
        corpus: list[str] = []
        for result in results[: self._fetch_limit]:
            try:
                page_title, paragraphs = await self._fetch.extract(result.url)
                snippet = " ".join(paragraphs)[:400]
                corpus.append(f"<source url={result.url}>\n{snippet}\n</source>")
                sources.append(
                    ResearchSource(
                        url=result.url,
                        title=page_title or result.title or result.url,
                        snippet=snippet or result.snippet,
                        tier=tier_for_url(result.url),
                        relevance=0.9,
                        fetched=True,
                    )
                )
            except Exception as exc:
                logger.info("fetch failed for %s: %s", result.url, exc)
                sources.append(
                    ResearchSource(
                        url=result.url,
                        title=result.title or result.url,
                        snippet=result.snippet,
                        tier=tier_for_url(result.url),
                        relevance=0.6,
                        fetched=False,
                    )
                )

        claims, research_summary = await self._extract_claims(
            title=title, summary=summary, corpus=corpus, sources=sources
        )
        return ResearchPackage(
            query="; ".join(queries),
            summary=research_summary,
            sources=sources,
            claims=[ResearchClaim(text=c, source_urls=[s.url for s in sources]) for c in claims],
        )

    async def _extract_claims(
        self,
        *,
        title: str,
        summary: str | None,
        corpus: list[str],
        sources: list[ResearchSource],
    ) -> tuple[list[str], str]:
        fallback_text = " ".join(s.snippet for s in sources) or f"{title} {summary or ''}"
        if not corpus:
            fallback_claims, fallback_summary = _fallback_claims(fallback_text)
            return fallback_claims, fallback_summary
        prompt = (
            f"Title: {title}\n"
            f"Summary: {summary or 'N/A'}\n\n"
            "Raw text from related pages:\n" + "\n".join(corpus)
        )
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._provider.generate(
                    prompt,
                    system=_SYSTEM_PROMPT,
                    format=_CLAIMS_JSON_SCHEMA,
                    temperature=0.2,
                )
                data = _extract_json(response.text)
                payload = _ClaimsOutput(**data)
                return payload.claims, payload.summary
            except (LLMError, ValueError, ValidationError):
                if attempt >= self._max_retries:
                    break
        fallback_claims, fallback_summary = _fallback_claims(fallback_text)
        return fallback_claims, fallback_summary