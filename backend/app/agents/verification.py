"""VerificationAgent — verifies claims against collected evidence."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from app.services.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 1

_VERIFICATION_STATUSES = ("CONFIRMED", "LIKELY", "UNCONFIRMED", "CONTRADICTED")


@dataclass
class VerifiedClaim:
    claim_id: int
    claim_text: str
    status: str
    confidence: float
    reasoning: str
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    story_id: int
    claims: list[VerifiedClaim] = field(default_factory=list)
    overall_confidence: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "story_id": self.story_id,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text,
                    "status": c.status,
                    "confidence": c.confidence,
                    "reasoning": c.reasoning,
                    "supporting_sources": c.supporting_sources,
                    "contradicting_sources": c.contradicting_sources,
                }
                for c in self.claims
            ],
            "overall_confidence": self.overall_confidence,
            "summary": self.summary,
        }


class _VerificationOutput(BaseModel):
    claims: list[dict] = Field(min_length=1, max_length=20)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=1000)


_VERIFICATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "integer"},
                    "status": {"type": "string", "enum": list(_VERIFICATION_STATUSES)},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string"},
                    "supporting_sources": {"type": "array", "items": {"type": "string"}},
                    "contradicting_sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim_id", "status", "confidence", "reasoning"],
            },
            "minItems": 1,
            "maxItems": 20,
        },
        "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "summary": {"type": "string"},
    },
    "required": ["claims", "overall_confidence", "summary"],
}

_SYSTEM_PROMPT = (
    "You are the verification agent of an AI newsroom. Given a list of claims "
    "and their associated evidence/sources, verify each claim. For each claim:\n"
    "1. Determine status: CONFIRMED (strong evidence), LIKELY (some evidence), "
    "UNCONFIRMED (insufficient evidence), CONTRADICTED (evidence opposes claim)\n"
    "2. Assign confidence (0.0-1.0) based on source quality and quantity\n"
    "3. Provide brief reasoning\n"
    "4. List supporting and contradicting source URLs\n\n"
    "Rules:\n"
    "- Never fabricate sources\n"
    "- Prefer primary sources (official, government, academic)\n"
    "- Multiple independent sources increase confidence\n"
    "- Contradicting sources decrease confidence\n"
    "- Be conservative: when uncertain, use UNCONFIRMED\n\n"
    "Return ONLY a JSON object with keys: 'claims' (array), "
    "'overall_confidence' (float), 'summary' (string)."
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
        raise ValueError("verification output must be a JSON object")
    return parsed


def _coerce_status(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in _VERIFICATION_STATUSES:
            return normalized
    return "UNCONFIRMED"


def _heuristic_verification(
    claim_text: str,
    evidence_urls: list[str],
    evidence_texts: list[str],
) -> tuple[str, float, str]:
    num_sources = len(evidence_urls)
    text = f"{claim_text} {' '.join(evidence_texts)}".lower()

    contradiction_words = [
        "denied", "false", "incorrect", "refuted", "debunked",
        "misleading", "inaccurate", "untrue", "disputed",
    ]
    contradiction_count = sum(1 for word in contradiction_words if word in text)

    confirmation_words = [
        "confirmed", "verified", "announced", "official",
        "according to", "confirmed by", "stated", "reported",
    ]
    confirmation_count = sum(1 for word in confirmation_words if word in text)

    if contradiction_count > confirmation_count and contradiction_count >= 2:
        return "CONTRADICTED", 0.3, "Multiple contradiction indicators found."
    elif confirmation_count >= 2 and num_sources >= 2:
        return "CONFIRMED", 0.7, f"Supported by {num_sources} sources."
    elif confirmation_count >= 1 or num_sources >= 1:
        return "LIKELY", 0.5, f"Some supporting evidence from {num_sources} source(s)."
    else:
        return "UNCONFIRMED", 0.3, "Insufficient evidence to verify."


class VerificationAgent:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._provider = provider
        self._max_retries = max_retries

    async def verify(
        self,
        *,
        story_id: int,
        claims: list[dict],
    ) -> VerificationResult:
        if not claims:
            return VerificationResult(
                story_id=story_id,
                overall_confidence=0.0,
                summary="No claims to verify.",
            )

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._llm_verify(story_id=story_id, claims=claims)
                return result
            except (LLMError, ValueError, ValidationError):
                if attempt >= self._max_retries:
                    break

        return self._heuristic_verify(story_id=story_id, claims=claims)

    async def _llm_verify(
        self,
        *,
        story_id: int,
        claims: list[dict],
    ) -> VerificationResult:
        prompt = self._build_prompt(claims)
        response = await self._provider.generate(
            prompt,
            system=_SYSTEM_PROMPT,
            format=_VERIFICATION_JSON_SCHEMA,
            temperature=0.1,
        )
        data = _extract_json(response.text)
        payload = _VerificationOutput(**data)

        verified_claims = []
        for claim_data in payload.claims:
            claim_id = claim_data.get("claim_id")
            original = next((c for c in claims if c["claim_id"] == claim_id), None)
            claim_text = original["claim_text"] if original else f"Claim {claim_id}"

            verified_claims.append(
                VerifiedClaim(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    status=_coerce_status(claim_data.get("status")),
                    confidence=float(claim_data.get("confidence", 0.5)),
                    reasoning=str(claim_data.get("reasoning", "")),
                    supporting_sources=claim_data.get("supporting_sources", []),
                    contradicting_sources=claim_data.get("contradicting_sources", []),
                )
            )

        return VerificationResult(
            story_id=story_id,
            claims=verified_claims,
            overall_confidence=payload.overall_confidence,
            summary=payload.summary,
        )

    def _heuristic_verify(
        self,
        *,
        story_id: int,
        claims: list[dict],
    ) -> VerificationResult:
        verified_claims = []
        for claim_data in claims:
            status, confidence, reasoning = _heuristic_verification(
                claim_text=claim_data["claim_text"],
                evidence_urls=claim_data.get("evidence_urls", []),
                evidence_texts=claim_data.get("evidence_texts", []),
            )
            verified_claims.append(
                VerifiedClaim(
                    claim_id=claim_data["claim_id"],
                    claim_text=claim_data["claim_text"],
                    status=status,
                    confidence=confidence,
                    reasoning=f"Rule-based (LLM unavailable): {reasoning}",
                    supporting_sources=claim_data.get("evidence_urls", []),
                    contradicting_sources=[],
                )
            )

        avg_confidence = (
            sum(c.confidence for c in verified_claims) / len(verified_claims)
            if verified_claims
            else 0.0
        )

        return VerificationResult(
            story_id=story_id,
            claims=verified_claims,
            overall_confidence=avg_confidence,
            summary=f"Rule-based verification: {len(verified_claims)} claims assessed.",
        )

    def _build_prompt(self, claims: list[dict]) -> str:
        parts = ["Claims to verify:\n"]
        for claim_data in claims:
            parts.append(f"Claim ID: {claim_data['claim_id']}")
            parts.append(f"Text: {claim_data['claim_text']}")
            parts.append("Evidence sources:")
            for i, url in enumerate(claim_data.get("evidence_urls", [])[:5]):
                text = claim_data.get("evidence_texts", [])[i] if i < len(claim_data.get("evidence_texts", [])) else ""
                parts.append(f"  - {url}")
                if text:
                    parts.append(f"    Snippet: {text[:200]}")
            parts.append("")
        return "\n".join(parts)
