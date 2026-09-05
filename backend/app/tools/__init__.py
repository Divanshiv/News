"""Research tool abstraction (spec §23).

Agents call tools through these interfaces, never a concrete backend, so the
web-search backend or fetching strategy can be swapped without touching agent
logic. `build_research_tools` constructs the configured set from settings.
``WEB_SEARCH_BACKEND`` accepts a comma-separated fallback chain, e.g.
``duckduckgo,bing``.
"""

from dataclasses import dataclass

from .source_lookup import SourceLookupTool
from .text_extraction import TextExtractionTool
from .url_fetch import URLFetchTool
from .web_search import (
    BingWebSearch,
    DuckDuckGoWebSearch,
    FallbackWebSearch,
    SearchResult,
    SerperWebSearch,
    WebSearchTool,
)


@dataclass
class ResearchTools:
    search: WebSearchTool
    fetch: TextExtractionTool
    source_lookup: SourceLookupTool


def _backend_by_name(name: str) -> WebSearchTool:
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "duckduckgo": lambda: DuckDuckGoWebSearch(
            timeout=settings.web_search_timeout_seconds,
            retries=settings.web_search_retries,
        ),
        "bing": lambda: BingWebSearch(
            timeout=settings.web_search_timeout_seconds,
            retries=settings.web_search_retries,
        ),
        "serper": lambda: SerperWebSearch(
            api_key=settings.serper_api_key,
            timeout=settings.web_search_timeout_seconds,
            retries=settings.web_search_retries,
        ),
    }[name.strip().lower()]()


def build_research_tools() -> ResearchTools:
    from app.core.config import get_settings

    settings = get_settings()
    names = [n.strip().lower() for n in settings.web_search_backend.split(",") if n.strip()]
    if not names:
        names = ["duckduckgo"]
    backends: list[WebSearchTool] = []
    for name in names:
        if name == "serper" and not settings.serper_api_key:
            continue
        try:
            backends.append(_backend_by_name(name))
        except KeyError:
            from app.tools.web_search import WebSearchError

            raise WebSearchError(f"unknown web_search_backend: {name!r}") from None
    if not backends:
        backends = [
            DuckDuckGoWebSearch(
                timeout=settings.web_search_timeout_seconds,
                retries=settings.web_search_retries,
            )
        ]
    search: WebSearchTool
    search = backends[0] if len(backends) == 1 else FallbackWebSearch(backends)
    return ResearchTools(
        search=search,
        fetch=TextExtractionTool(max_chars=settings.research_text_max_chars),
        source_lookup=SourceLookupTool(),
    )


__all__ = [
    "BingWebSearch",
    "DuckDuckGoWebSearch",
    "FallbackWebSearch",
    "ResearchTools",
    "SearchResult",
    "SerperWebSearch",
    "SourceLookupTool",
    "TextExtractionTool",
    "URLFetchTool",
    "WebSearchTool",
    "build_research_tools",
]
