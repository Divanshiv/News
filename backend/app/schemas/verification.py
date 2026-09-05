from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evidence_text: str
    url: str | None = None
    source_id: int | None = None


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_text: str
    status: str
    confidence_score: float | None = None
    evidences: list[EvidenceRead] = []


class ClaimUpdate(BaseModel):
    status: str | None = None
    confidence_score: float | None = None


class VerifiedClaimRead(BaseModel):
    claim_id: int
    claim_text: str
    status: str
    confidence: float
    reasoning: str
    supporting_sources: list[str] = []
    contradicting_sources: list[str] = []


class StoryVerificationRead(BaseModel):
    story_id: int
    title: str
    claims: list[ClaimRead] = []
    overall_confidence: float = 0.0
    verification_summary: str = ""


class VerificationRunResponse(BaseModel):
    job_id: str
    job_name: str
    status: str
    story_id: int | None = None
