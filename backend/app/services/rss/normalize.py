"""Normalization helpers for RSS ingestion: canonical URLs and plain-text titles."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "ref_url",
}

DEFAULT_PORTS = {"http": "80", "https": "443"}


def canonicalize_url(raw: str | None) -> str | None:
    """Normalize a URL for deduplication, or None if it cannot be used.

    Applies scheme/host lowercasing, default-port removal, tracking-parameter
    stripping, fragment removal, and trailing-slash removal on non-root paths.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https") or not parts.netloc:
        return None
    hostname = parts.hostname
    if hostname is None:
        return None
    host = hostname.lower()
    port = parts.port
    if port is None:
        netloc = host
    elif str(port) == DEFAULT_PORTS.get(scheme):
        netloc = host
    else:
        netloc = f"{host}:{port}"
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    )
    path = parts.path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, netloc, path, query, ""))


_WS_RE = re.compile(r"\s+")


def normalize_title(title: str | None) -> str:
    """Collapse whitespace and fold case so near-identical titles compare equal."""
    if not title:
        return ""
    return _WS_RE.sub(" ", title).strip().casefold()