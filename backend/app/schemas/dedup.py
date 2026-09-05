from pydantic import BaseModel


class DedupMergeRequest(BaseModel):
    keep_id: int
    absorb_id: int


class DedupMergeResponse(BaseModel):
    keep_id: int
    keep_title: str
    absorbed_id: int
    absorbed_title: str
    moved_links: int
    demoted_primary: bool


class DedupCandidateRead(BaseModel):
    story_id_a: int
    title_a: str
    story_id_b: int
    title_b: str
    score: float