from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    agent_name: str
    status: str
    output: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchSourceRead(BaseModel):
    source_id: int
    name: str | None = None
    url: str | None = None
    relationship: str
    relevance_score: float | None = None


class EvidenceRead(BaseModel):
    id: int
    evidence_text: str
    url: str | None = None
    source_id: int | None = None


class ClaimRead(BaseModel):
    id: int
    claim_text: str
    status: str
    confidence_score: float | None = None
    evidences: list[EvidenceRead] = []


class StoryResearchRead(BaseModel):
    story_id: int
    title: str
    runs: list[ResearchRunRead] = []
    sources: list[ResearchSourceRead] = []
    claims: list[ClaimRead] = []