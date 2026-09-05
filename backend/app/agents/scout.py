from __future__ import annotations

import json
import re
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError

from app.models.source import SOURCE_CATEGORIES
from app.services.llm.base import LLMError, LLMProvider

DEFAULT_MAX_RETRIES = 1


class ScoutVerdict(BaseModel):
    should_research: bool
    importance: int = Field(ge=0, le=10)
    category: str | None = Field(default=None, max_length=50)
    reason: str = Field(min_length=1, max_length=500)


_SCOUT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "should_research": {"type": "boolean"},
        "importance": {"type": "integer", "minimum": 0, "maximum": 10},
        "category": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["should_research", "importance", "category", "reason"],
}

_SYSTEM_PROMPT = (
    "You are the scout agent of an AI newsroom. Grade one news story. "
    "Be strict: a story deserves research only if it is significant, "
    "actionable, or likely to spread. Return ONLY a JSON object with keys: "
    '"should_research" (bool), "importance" (int 0-10), '
    f'"category" (one of {", ".join(SOURCE_CATEGORIES)}), "reason" (one short sentence).'
)

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "AI",
        (
            "openai",
            "anthropic",
            "google deepmind",
            "gpt",
            "claude",
            "llm",
            "machine learning",
            "chatbot",
            "artificial intelligence",
        ),
    ),
    (
        "Cybersecurity",
        (
            "breach",
            "ransomware",
            "hack",
            "malware",
            "zero-day",
            "vulnerability",
            "cyber",
            "phishing",
        ),
    ),
    (
        "Space",
        ("nasa", "isro", "rocket", "satellite", "spacex", "mars", "orbit"),
    ),
    (
        "Business",
        (
            "funding",
            "raises",
            "acquisition",
            "merger",
            "ipo",
            "startup",
            "revenue",
            "investor",
        ),
    ),
    ("India", ("india", "delhi", "mumbai", "bangalore", "bengaluru", "rupee", "modi")),
    (
        "Science",
        ("research", "study", "scientists", "quantum", "gene", "clinical trial", "telescope", "vaccine"),
    ),
    ("World", ("united nations", "europe", "election", "diplomat", "sanction", "conflict")),
    (
        "Technology",
        ("chip", "semiconductor", "smartphone", "robot", "software", "internet", "processor", "5g"),
    ),
)

_IMPORTANCE_RULES: tuple[tuple[int, tuple[str, ...]], ...] = (
    (9, ("breach", "ransomware", "zero-day", "hacked", "exploit")),
    (8, ("funding", "raises", "acquisition", "merger", "ipo")),
    (7, ("launches", "announced", "unveils", "releases", "ban", "lawsuit", "regulation")),
    (5, ("study", "research", "report", "survey", "update")),
)


def _build_prompt(
    *,
    title: str,
    summary: str | None,
    category_hint: str | None,
    published_at: datetime | None,
) -> str:
    parts = [f"Title: {title}"]
    if summary and summary.strip():
        parts.append(f"Summary: {summary.strip()}")
    if category_hint:
        parts.append(f"Source category hint: {category_hint}")
    if published_at:
        parts.append(f"Published: {published_at.isoformat()}")
    return "\n".join(parts)


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
        raise ValueError("scout output must be a JSON object")
    return parsed


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _coerce_category(value: object, fallback: str | None) -> str | None:
    if isinstance(value, str):
        for candidate in SOURCE_CATEGORIES:
            if value.strip().lower() == candidate.lower():
                return candidate
    return fallback if fallback in SOURCE_CATEGORIES else None


def _fallback_verdict(
    *, title: str, summary: str | None, category_hint: str | None
) -> ScoutVerdict:
    text = f"{title} {summary or ''}".lower()
    votes = {
        category: sum(1 for keyword in keywords if keyword in text)
        for category, keywords in _CATEGORY_KEYWORDS
    }
    category = max(votes, key=votes.get) if any(votes.values()) else category_hint
    if category not in SOURCE_CATEGORIES:
        category = "Technology"
    match = next(
        (
            (boost, keyword)
            for boost, keywords in _IMPORTANCE_RULES
            for keyword in keywords
            if keyword in text
        ),
        None,
    )
    importance = match[0] if match else 4
    return ScoutVerdict(
        should_research=importance >= 6,
        importance=importance,
        category=category,
        reason=(
            f"Rule-based estimate (LLM unavailable): matched '{match[1]}', "
            f"importance {importance}/10."
            if match
            else "Rule-based estimate (LLM unavailable): no strong signal."
        ),
    )


class ScoutAgent:
    def __init__(
        self, provider: LLMProvider, *, max_retries: int = DEFAULT_MAX_RETRIES
    ) -> None:
        self._provider = provider
        self._max_retries = max_retries

    async def scout(
        self,
        *,
        title: str,
        summary: str | None = None,
        category_hint: str | None = None,
        published_at: datetime | None = None,
    ) -> ScoutVerdict:
        prompt = _build_prompt(
            title=title,
            summary=summary,
            category_hint=category_hint,
            published_at=published_at,
        )
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._provider.generate(
                    prompt,
                    system=_SYSTEM_PROMPT,
                    format=_SCOUT_JSON_SCHEMA,
                    temperature=0.2,
                )
                return self._parse(response.text, category_hint)
            except (LLMError, ValueError, ValidationError):
                if attempt >= self._max_retries:
                    break
        return _fallback_verdict(
            title=title, summary=summary, category_hint=category_hint
        )

    def _parse(self, text: str, category_hint: str | None) -> ScoutVerdict:
        try:
            data = _extract_json(text)
            return ScoutVerdict(
                should_research=_coerce_bool(data["should_research"]),
                importance=int(data["importance"]),
                category=_coerce_category(data.get("category"), category_hint),
                reason=str(data["reason"]),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise ValueError(f"invalid scout payload: {exc}") from exc