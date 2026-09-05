import pytest

from app.agents.research import (
    ResearchAgent,
    _ClaimsOutput,
    _extract_json,
    build_queries,
    _dedupe_results,
    osint_fallback_queries,
)
from app.services.llm.base import LLMError, LLMResponse
from app.tools import SearchResult

SAMPLE_JSON = (
    '{"claims": ["Company X announced product Y.", "Product Y launches on '
    'December 1."], "summary": "Company X unveiled its new product."}'
)


class FakeProvider:
    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0
        self.kwargs = None

    async def generate(self, prompt, **kwargs):
        self.kwargs = kwargs
        response = self._responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


class FakeSearch:
    def __init__(self, results):
        self._results = results
        self.queries = []

    async def search(self, query, limit=10):
        self.queries.append(query)
        return self._results


class FakeFetch:
    def __init__(self, title="Page title", paragraphs=("First paragraph.", "Second paragraph.")):
        self.title = title
        self.paragraphs = paragraphs
        self.urls = []

    async def extract(self, url):
        self.urls.append(url)
        return self.title, list(self.paragraphs)


def test_build_queries_always_includes_title():
    queries = build_queries(title="OpenAI launches model", summary=None, category="AI")
    assert queries[0] == "OpenAI launches model"
    assert len(queries) >= 2


def test_osint_fallback_queries_for_known_category():
    queries = osint_fallback_queries(title="Solar flare hits Earth", category="Space")
    assert queries == [
        "Solar flare hits Earth site:nasa.gov",
        "Solar flare hits Earth site:spacenews.com",
    ]


def test_osint_fallback_queries_empty_for_unknown_category():
    assert osint_fallback_queries(title="Anything", category="Cooking") == []


def test_extract_json_handles_fenced_output():
    data = _extract_json(f"```json\n{SAMPLE_JSON}\n```")
    assert data["claims"][0].startswith("Company X")


def test_dedupe_results_removes_duplicates_and_tracking():
    results = [
        SearchResult(title="A", url="https://example.com/x?utm_source=a", snippet=""),
        SearchResult(title="A dup", url="https://example.com/x", snippet=""),
        SearchResult(title="Search engine", url="https://html.duckduckgo.com/html/?q=1", snippet=""),
        SearchResult(title="B", url="https://other.org/y", snippet=""),
    ]
    deduped = _dedupe_results(results)
    assert len(deduped) == 2


async def test_research_agent_structure():
    results = [
        SearchResult(title="ACME press release", url="https://acme.com/press", snippet="ACME announced product Y today."),
        SearchResult(title="Tech blog", url="https://blog.example/analysis", snippet="Product Y launches December 1."),
        SearchResult(title="Forum chatter", url="https://forum.example/topic", snippet="people talking"),
    ]
    agent = ResearchAgent(
        FakeProvider(LLMResponse(text=SAMPLE_JSON, model="m")),
        FakeSearch(results),
        FakeFetch(),
        max_queries=2,
        fetch_limit=2,
        max_sources=3,
    )
    package = await agent.research(title="ACME launches product Y", category="AI")

    assert len(package.sources) >= 2
    assert any("acme.com" in s.url for s in package.sources)
    assert len(package.claims) == 2
    assert package.summary.startswith("Company X")
    fetched = [s for s in package.sources if s.fetched]
    assert len(fetched) == 2


async def test_research_agent_falls_back_when_llm_unavailable():
    results = [
        SearchResult(title="ACME press release", url="https://acme.com/press", snippet="ACME announced its new product today with a launch date next month."),
        SearchResult(title="Tech blog", url="https://blog.example/analysis", snippet="The product includes several features."),
    ]
    agent = ResearchAgent(
        FakeProvider(LLMError("down"), LLMError("down")),
        FakeSearch(results),
        FakeFetch(),
        max_sources=2,
        fetch_limit=2,
    )
    package = await agent.research(title="ACME product")

    assert package.claims
    assert package.summary


async def test_research_agent_survives_failed_fetches():
    class FlakyFetch:
        async def extract(self, url):
            raise RuntimeError("network down")

    results = [
        SearchResult(title="Only source", url="https://acme.com/press", snippet="A snippet long enough to count as a fallback claim when no page text is available and the LLM is also down."),
    ]
    agent = ResearchAgent(
        FakeProvider(LLMError("down"), LLMError("down")),
        FakeSearch(results),
        FlakyFetch(),
        max_sources=2,
    )
    package = await agent.research(title="ACME product")
    assert len(package.sources) == 1
    assert package.sources[0].fetched is False
    assert package.claims


class ThinSearch:
    def __init__(self):
        self.queries = []

    async def search(self, query, limit=10):
        self.queries.append(query)
        if "site:" in query:
            return [
                SearchResult(
                    title="NASA page",
                    url="https://www.nasa.gov/news",
                    snippet="A useful snippet about the event from nasa.gov.",
                )
            ]
        return []


async def test_research_agent_runs_osint_fallback_when_results_thin():
    search = ThinSearch()
    agent = ResearchAgent(
        FakeProvider(LLMError("down"), LLMError("down")),
        search,
        FakeFetch(),
        max_queries=1,
        max_sources=2,
    )
    package = await agent.research(title="Solar flare hits Earth", category="Space")
    assert any("site:nasa.gov" in q for q in search.queries)
    assert any("nasa.gov" in s.url for s in package.sources)
    assert package.claims


async def test_research_agent_retries_malformed_llm_output():
    provider = FakeProvider(
        LLMResponse(text="not json at all", model="m"),
        LLMResponse(text=SAMPLE_JSON, model="m"),
    )
    results = [SearchResult(title="T", url="https://a.com/1", snippet="snippet text here")]
    agent = ResearchAgent(provider, FakeSearch(results), FakeFetch(), max_sources=1)
    package = await agent.research(title="story")
    assert len(package.claims) == 2
    assert provider.calls == 2


def test_claims_output_validation():
    payload = _ClaimsOutput(**{"claims": ["c1", "c2"], "summary": "s"})
    assert len(payload.claims) == 2
    with pytest.raises(ValueError):
        _ClaimsOutput(**{"claims": [], "summary": "s"})