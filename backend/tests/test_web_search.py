import asyncio

import httpx
import pytest

from app.tools.web_search import (
    BingWebSearch,
    DuckDuckGoWebSearch,
    FallbackWebSearch,
    SearchResult,
    SerperWebSearch,
    WebSearchError,
    _BingParser,
    _DuckDuckGoParser,
    _resolve_bing_url,
)

_DDG_HTML = """
<html><body>
<div class="result">
  <a class="result__a" href="https://example.com/news/1?utm_source=x&ref=y">Example News Headline</a>
  <a class="result__snippet">The full snippet text about the event.</a>
</div>
<div class="result">
  <a class="result__a" href="https://other.org/story">Other report</a>
  <a class="result__snippet">A shorter snippet.</a>
</div>
</body></html>
"""


def test_ddg_parser_extracts_results():
    parser = _DuckDuckGoParser()
    parser.feed(_DDG_HTML)
    assert [r.title for r in parser.results] == [
        "Example News Headline",
        "Other report",
    ]
    assert parser.results[0].url == "https://example.com/news/1?utm_source=x&ref=y"
    assert "full snippet" in parser.results[0].snippet


async def test_duckduckgo_search_parses_mock_response():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=_DDG_HTML)
        )
    )
    tool = DuckDuckGoWebSearch(client=client)
    results = await tool.search("openai announces model", limit=10)
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "Example News Headline"
    assert results[0].url.startswith("https://example.com")
    await tool.close()


async def test_duckduckgo_search_retries_then_raises():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(200, text=_DDG_HTML)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tool = DuckDuckGoWebSearch(client=client, retries=2, backoff=0)
    results = await tool.search("query")
    assert calls >= 2
    assert len(results) == 2
    await tool.close()


async def test_duckduckgo_search_exhausts_retries():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(500)
        )
    )
    tool = DuckDuckGoWebSearch(client=client, retries=1, backoff=0)
    with pytest.raises(WebSearchError):
        await tool.search("query")
    await tool.close()


async def test_serper_search_parses_organic_results():
    def handler(request):
        assert request.headers["X-API-KEY"] == "secret"
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "organic": [
                    {"title": "T1", "link": "https://a.com/1", "snippet": "S1"},
                    {"title": "T2", "link": "https://b.com/2", "snippet": "S2"},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tool = SerperWebSearch(api_key="secret", client=client)
    results = await tool.search("query", limit=5)
    assert [r.title for r in results] == ["T1", "T2"]
    assert results[0].url == "https://a.com/1"
    assert results[0].snippet == "S1"
    await tool.close()


async def test_serper_search_respects_limit():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "organic": [
                    {"title": f"T{i}", "link": f"https://a.com/{i}", "snippet": ""}
                    for i in range(5)
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tool = SerperWebSearch(api_key="k", client=client)
    results = await tool.search("query", limit=2)
    assert len(results) == 2
    await tool.close()


def test_resolve_bing_url_decodes_base64_u_param():
    href = (
        "https://www.bing.com/ck/a?q=openai&u=aHR0cHM6Ly9vcGVuYWkuY29tLw&ntb=1"
    )
    assert _resolve_bing_url(href) == "https://openai.com/"


def test_resolve_bing_url_pads_legacy_padding():
    href = "https://www.bing.com/ck/a?u=aHR0cHM6Ly9vcGVuYWkuY29tLw%3d%3d&ntb=1"
    assert _resolve_bing_url(href) == "https://openai.com/"


def test_resolve_bing_url_strips_a1_marker():
    href = "https://www.bing.com/ck/a?q=openai&u=a1aHR0cHM6Ly9vcGVuYWkuY29tLw&ntb=1"
    assert _resolve_bing_url(href) == "https://openai.com/"


def test_resolve_bing_url_passthrough_non_redirect():
    assert _resolve_bing_url("https://example.org/story") == "https://example.org/story"
    assert _resolve_bing_url("https://www.bing.com/ck/a?ntb=1") == (
        "https://www.bing.com/ck/a?ntb=1"
    )


_BING_HTML = """
<html><body>
<ol id="b_results">
<li class="b_algo">
  <h2>
    <a href="https://www.bing.com/ck/a?q=openai&u=aHR0cHM6Ly9vcGVuYWkuY29tLw&ntb=1">
      OpenAI
    </a>
  </h2>
  <div class="b_caption"><p class="b_lineclamp2">OpenAI is an AI research lab.</p></div>
</li>
<li class="b_algo">
  <h2><a href="https://other.org/report">Other report</a></h2>
  <div class="b_caption"><p class="b_lineclamp3">No redirect needed here.</p></div>
</li>
<li class="b_algo">
  <h2><a href="https://www.bing.com/ck/a?q=x">Anchor with no u param</a></h2>
  <p class="b_lineclamp2">Resolves to its own href (passthrough, no u to decode).</p>
</li>
<li class="b_pag">Not a real result.</li>
</ol>
</body></html>
"""


def test_bing_parser_extracts_results_and_decodes_urls():
    parser = _BingParser()
    parser.feed(_BING_HTML)
    assert [r.title for r in parser.results] == [
        "OpenAI",
        "Other report",
        "Anchor with no u param",
    ]
    assert parser.results[0].url == "https://openai.com/"
    assert parser.results[1].url == "https://other.org/report"
    assert parser.results[2].url == "https://www.bing.com/ck/a?q=x"
    assert "AI research lab" in parser.results[0].snippet


async def test_bing_search_parses_mock_response():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=_BING_HTML)
        )
    )
    tool = BingWebSearch(client=client)
    results = await tool.search("openai", limit=10)
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "OpenAI"
    assert results[0].url == "https://openai.com/"
    await tool.close()


async def test_bing_search_exhausts_retries():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )
    tool = BingWebSearch(client=client, retries=1, backoff=0)
    with pytest.raises(WebSearchError):
        await tool.search("query")
    await tool.close()


def _raise_timeout(request):
    raise httpx.ConnectTimeout("", request=request)


async def test_duckduckgo_error_message_includes_exception_type():
    client = httpx.AsyncClient(transport=httpx.MockTransport(_raise_timeout))
    tool = DuckDuckGoWebSearch(client=client, retries=1, backoff=0)
    with pytest.raises(WebSearchError) as excinfo:
        await tool.search("query")
    message = str(excinfo.value)
    assert "ConnectTimeout" in message
    assert not message.endswith(": ")
    await tool.close()


def test_fallback_uses_first_backend_results():
    failing = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ),
        retries=0,
        backoff=0,
    )
    working = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text=_DDG_HTML)
            )
        )
    )
    chain = FallbackWebSearch([failing, working])
    results = asyncio.run(chain.search("query"))
    assert [r.title for r in results] == ["Example News Headline", "Other report"]
    asyncio.run(chain.close())


def test_fallback_skips_empty_first_backend():
    empty = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text="<html></html>")
            )
        )
    )
    working = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text=_DDG_HTML)
            )
        )
    )
    chain = FallbackWebSearch([empty, working])
    results = asyncio.run(chain.search("query"))
    assert len(results) == 2
    asyncio.run(chain.close())


def test_fallback_aggregates_all_failures():
    first = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(_raise_timeout)
        ),
        retries=0,
        backoff=0,
    )
    second = DuckDuckGoWebSearch(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
        retries=0,
        backoff=0,
    )
    chain = FallbackWebSearch([first, second])
    with pytest.raises(WebSearchError) as excinfo:
        asyncio.run(chain.search("query"))
    message = str(excinfo.value)
    assert "all web search backends failed" in message
    assert message.count("DuckDuckGoWebSearch:") == 2
    asyncio.run(chain.close())