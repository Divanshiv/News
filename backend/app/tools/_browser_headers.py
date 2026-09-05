"""Browser-like request headers shared by the HTTP-based research tools.

Keyless HTML search endpoints (DuckDuckGo, Bing) and arbitrary publisher sites
are far more tolerant of a real browser UA than of httpx's default
``python-httpx/x``, which is often rejected outright.
"""

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

__all__ = ["BROWSER_HEADERS"]