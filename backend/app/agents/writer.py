"""WriterAgent — drafts a news article from a verified research package.

The agent takes a story plus its verified claims and evidence, and produces the
article sections defined by the spec (headline, summary, what happened, key
details, why it matters, what happens next, how we know, sources). The LLM is
used when available with a deterministic template fallback, so article
generation runs anywhere. The agent never invents facts: it only uses the
provided claims/evidence.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from app.services.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 1


@dataclass
class ArticleDraft:
    headline: str
    subheadline: str
    summary: str
    body: str
    seo_title: str
    seo_description: str

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "subheadline": self.subheadline,
            "summary": self.summary,
            "body": self.body,
            "seo_title": self.seo_title,
            "seo_description": self.seo_description,
        }


class _WriterOutput(BaseModel):
    headline: str = Field(min_length=1, max_length=500)
    subheadline: str = Field(default="", max_length=500)
    summary: str = Field(min_length=1)
    what_happened: str = Field(min_length=1)
    key_details: list[str] = Field(min_length=1, max_length=12)
    why_it_matters: str = Field(min_length=1)
    what_happens_next: str = Field(default="", max_length=1000)
    how_we_know: str = Field(min_length=1)
    sources: list[str] = Field(min_length=0, max_length=20)
    seo_title: str = Field(default="", max_length=500)
    seo_description: str = Field(default="", max_length=1000)


_WRITER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "subheadline": {"type": "string"},
        "summary": {"type": "string"},
        "what_happened": {"type": "string"},
        "key_details": {"type": "array", "items": {"type": "string"}},
        "why_it_matters": {"type": "string"},
        "what_happens_next": {"type": "string"},
        "how_we_know": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
        "seo_title": {"type": "string"},
        "seo_description": {"type": "string"},
    },
    "required": [
        "headline",
        "summary",
        "what_happened",
        "key_details",
        "why_it_matters",
        "how_we_know",
    ],
}

_SYSTEM_PROMPT = (
    "You are the writer agent of an AI newsroom. Given a news story, its "
    "verified claims, and evidence, write a factual, neutral, readable news "
    "article. You MUST use ONLY the provided claims and evidence. Never invent "
    "quotes, numbers, dates, people, locations, events, or sources. "
    "Be concise. No clickbait. No unsupported claims.\n\n"
    "Return ONLY a JSON object with the following keys:\n"
    "- headline (string)\n"
    "- subheadline (string)\n"
    "- summary (one short paragraph)\n"
    "- what_happened (main narrative, a few paragraphs)\n"
    "- key_details (array of short bullet strings)\n"
    "- why_it_matters (paragraph)\n"
    "- what_happens_next (string, may be empty)\n"
    "- how_we_know (methodology paragraph mentioning source tiers)\n"
    "- sources (array of source URLs used)\n"
    "- seo_title (string <= 60 chars)\n"
    "- seo_description (string <= 160 chars)"
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
        raise ValueError("writer output must be a JSON object")
    return parsed


def _as_paragraphs(text: str) -> str:
    return "\n\n".join(p.strip() for p in text.split("\n") if p.strip())


def _join_sections(sections: dict) -> str:
    blocks = []
    for heading in ("what_happened", "why_it_matters", "what_happens_next"):
        value = (sections.get(heading) or "").strip()
        if value:
            blocks.append(f"## {heading.replace('_', ' ').title()}\n\n{value}")
    if sections.get("key_details"):
        bullets = "\n".join(f"- {item}" for item in sections["key_details"])
        blocks.append(f"## Key Details\n\n{bullets}")
    how_we_know = (sections.get("how_we_know") or "").strip()
    if how_we_know:
        blocks.append(f"## How We Know\n\n{how_we_know}")
    sources = sections.get("sources") or []
    if sources:
        source_lines = "\n".join(f"- {url}" for url in sources)
        blocks.append(f"## Sources\n\n{source_lines}")
    return "\n\n".join(blocks)


def _fallback_article(
    *,
    title: str,
    summary: str,
    claims: list[dict],
    source_urls: list[str],
) -> _WriterOutput:
    confirmed_claims = [
        c["claim_text"] for c in claims if c.get("status") in ("CONFIRMED", "LIKELY")
    ] or [c["claim_text"] for c in claims]
    key_details = [c[:240] for c in confirmed_claims[:8]]
    what_happened = " ".join(confirmed_claims) or f"{title}. " + (summary or "")
    details = key_details or ([summary[:240]] if summary else [title[:240]])
    why_it_matters = (
        f"This story matters because it concerns {title.lower()}. "
        f"{summary[:240]}" if summary else f"This story matters because it concerns {title.lower()}."
    )
    how_we_know = (
        "This article is based on verified claims and supporting evidence "
        "collected from the listed sources. Every statement is traceable to "
        "the evidence recorded during research and verification."
    )
    seo_title = title[:60]
    seo_description = summary[:160] or title[:160]
    return _WriterOutput(
        headline=title[:500],
        subheadline="",
        summary=(summary or confirmed_claims[0][:300]) if (summary or confirmed_claims) else title,
        what_happened=what_happened.strip() or title,
        key_details=details,
        why_it_matters=why_it_matters,
        what_happens_next="",
        how_we_know=how_we_know,
        sources=source_urls[:20],
        seo_title=seo_title,
        seo_description=seo_description,
    )


class WriterAgent:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._provider = provider
        self._max_retries = max_retries

    async def write(
        self,
        *,
        title: str,
        summary: str | None,
        category: str | None,
        claims: list[dict],
        source_urls: list[str],
    ) -> ArticleDraft:
        for attempt in range(self._max_retries + 1):
            try:
                result = await self._llm_write(
                    title=title,
                    summary=summary,
                    category=category,
                    claims=claims,
                    source_urls=source_urls,
                )
                return self._to_draft(result)
            except (LLMError, ValueError, ValidationError):
                if attempt >= self._max_retries:
                    break

        fallback = _fallback_article(
            title=title, summary=summary or "", claims=claims, source_urls=source_urls
        )
        return self._to_draft(fallback)

    async def _llm_write(
        self,
        *,
        title: str,
        summary: str | None,
        category: str | None,
        claims: list[dict],
        source_urls: list[str],
    ) -> _WriterOutput:
        prompt = self._build_prompt(
            title=title, summary=summary, category=category, claims=claims, source_urls=source_urls
        )
        response = await self._provider.generate(
            prompt,
            system=_SYSTEM_PROMPT,
            format=_WRITER_JSON_SCHEMA,
            temperature=0.4,
        )
        data = _extract_json(response.text)
        return _WriterOutput(**data)

    def _to_draft(self, output: _WriterOutput) -> ArticleDraft:
        return ArticleDraft(
            headline=output.headline,
            subheadline=output.subheadline,
            summary=output.summary,
            body=_join_sections(output.model_dump()),
            seo_title=output.seo_title or output.headline[:60],
            seo_description=output.seo_description or output.summary[:160],
        )

    def _build_prompt(
        self,
        *,
        title: str,
        summary: str | None,
        category: str | None,
        claims: list[dict],
        source_urls: list[str],
    ) -> str:
        parts = [f"Story title: {title}\n"]
        parts.append(f"Category: {category or 'N/A'}")
        parts.append(f"Summary: {summary or 'N/A'}\n\n")
        parts.append("Verified claims:")
        for claim in claims:
            parts.append(
                f"- [{claim.get('status', 'UNCONFIRMED')}] "
                f"confidence={claim.get('confidence', 0.0)}: {claim['claim_text']}"
            )
        if source_urls:
            parts.append("\nSources used:")
            for url in source_urls:
                parts.append(f"- {url}")
        return "\n".join(parts)
