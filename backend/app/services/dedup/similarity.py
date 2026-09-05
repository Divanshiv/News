"""Cross-source story similarity scoring (stdlib-only)."""

import re

from difflib import SequenceMatcher

from app.services.rss.normalize import normalize_title

TITLE_STRONG = 0.85
TITLE_WEAK = 0.75
DESC_MIN = 0.75
CONTAIN_MIN = 0.75
CONTAIN_MIN_TOKENS = 3
REVIEW_MIN = 0.70

STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "from", "as"}
)

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def tokenize(title: str) -> frozenset[str]:
    normalized = normalize_title(title)
    if not normalized:
        return frozenset()
    return frozenset(
        token
        for token in _NON_WORD.sub(" ", normalized).split()
        if token not in STOPWORDS
    )


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = tokenize(a), tokenize(b)
    jaccard = 0.0
    if ta and tb:
        union = ta | tb
        if union:
            jaccard = len(ta & tb) / len(union)
    sequence = SequenceMatcher(None, na, nb).ratio()
    return max(jaccard, sequence)


def description_similarity(a: str | None, b: str | None) -> float | None:
    na = normalize_title(a or "")
    nb = normalize_title(b or "")
    if not na or not nb or min(len(na), len(nb)) < 20:
        return None
    # Long summaries dominate SequenceMatcher cost (O(n*m)); cap at a fixed
    # window so duplicate decisions stay fast even with thousands of pairs.
    na = na[:_DESC_MAX_CHARS]
    nb = nb[:_DESC_MAX_CHARS]
    return SequenceMatcher(None, na, nb).ratio()


_DESC_MAX_CHARS = 140


def token_containment(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    larger = max(len(ta), len(tb))
    return overlap / larger if larger else 0.0


def is_same_event(title_a, summary_a, title_b, summary_b) -> bool:
    if title_similarity(title_a, title_b) >= TITLE_STRONG:
        return True
    if title_similarity(title_a, title_b) >= TITLE_WEAK:
        desc = description_similarity(summary_a, summary_b)
        if desc is not None and desc >= DESC_MIN:
            return True
    ta, tb = tokenize(title_a), tokenize(title_b)
    if (
        len(ta) >= CONTAIN_MIN_TOKENS
        and len(tb) >= CONTAIN_MIN_TOKENS
        and token_containment(title_a, title_b) >= CONTAIN_MIN
    ):
        return True
    return False


def pair_score(title_a, summary_a, title_b, summary_b) -> float:
    tsim = title_similarity(title_a, title_b)
    desc = description_similarity(summary_a, summary_b)
    if desc is None:
        return tsim
    return 0.7 * tsim + 0.3 * desc