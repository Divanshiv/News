import httpx

from app.tools.text_extraction import TextExtractionTool
from app.tools.url_fetch import URLFetchError, URLFetchTool

_HTML = """<html><head><title>Example News</title>
<style>body { color: red; }</style>
</head><body>
<nav><a href="/">Home</a></nav>
<article>
  <h1>Company announces new product</h1>
  <p>The company announced the product on Monday.</p>
  <p>It launches next month with early access.</p>
</article>
<script>alert('nope');</script>
</body></html>"""


async def test_url_fetch_returns_text():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=_HTML)
        )
    )
    tool = URLFetchTool(client=client)
    assert "Company announces" in await tool.fetch("https://example.com/a")
    await tool.close()


async def test_url_fetch_raises_on_http_error():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(404))
    )
    tool = URLFetchTool(client=client, retries=0)
    try:
        await tool.fetch("https://example.com/missing")
        assert False, "expected URLFetchError"
    except URLFetchError:
        pass
    finally:
        await tool.close()


async def test_text_extraction_strips_markup_and_scripts():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=_HTML)
        )
    )
    tool = TextExtractionTool(fetcher=URLFetchTool(client=client))
    title, paragraphs = await tool.extract("https://example.com/a")
    assert title == "Example News"
    text = " ".join(paragraphs).lower()
    assert "company announces new product" in text
    assert "alert('nope')" not in text
    assert "body { color" not in text
    assert "Home" not in text
    await tool.close()


async def test_text_extraction_caps_length():
    big = "<html><body>" + "".join(f"<p>paragraph {i} padding text</p>" for i in range(2000)) + "</body></html>"
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=big))
    )
    tool = TextExtractionTool(fetcher=URLFetchTool(client=client), max_chars=500)
    title, paragraphs = await tool.extract("https://example.com/long")
    total = sum(len(p) for p in paragraphs)
    assert total <= 520
    await tool.close()