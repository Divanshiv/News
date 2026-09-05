import pytest

from app.agents.writer import WriterAgent, _WRITER_JSON_SCHEMA
from app.services.llm.base import LLMError, LLMResponse

VALID_JSON = (
    '{"headline": "Company X Announces Product Y", "subheadline": "New launch set for December", '
    '"summary": "Company X unveiled Product Y today.", '
    '"what_happened": "Company X announced Product Y at its annual event.", '
    '"key_details": ["Product Y launches December 1.", "Product Y supports feature Z."], '
    '"why_it_matters": "The launch expands the market.", '
    '"what_happens_next": "Shipping begins in December.", '
    '"how_we_know": "Based on the official announcement.", '
    '"sources": ["https://example.com/press"], '
    '"seo_title": "Company X Announces Product Y", '
    '"seo_description": "Company X unveiled Product Y at its annual event."}'
)


class FakeProvider:
    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = 0
        self.kwargs = None
        self.prompt = None

    async def generate(self, prompt, **kwargs):
        self.kwargs = kwargs
        self.prompt = prompt
        response = self._responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


SAMPLE_CLAIMS = [
    {
        "claim_id": 1,
        "claim_text": "Company X announced a new product.",
        "status": "CONFIRMED",
        "confidence": 0.9,
        "evidence_urls": ["https://example.com/announcement"],
    }
]

BASE_KWARGS = {
    "title": "Company X announces product Y",
    "summary": "Company X unveiled product Y.",
    "category": "AI",
    "claims": SAMPLE_CLAIMS,
    "source_urls": ["https://example.com/announcement"],
}


async def test_writer_parses_valid_json():
    provider = FakeProvider(LLMResponse(text=VALID_JSON, model="m"))
    agent = WriterAgent(provider)
    draft = await agent.write(**BASE_KWARGS)

    assert draft.headline == "Company X Announces Product Y"
    assert "Product Y launches December 1." in draft.body
    assert "## How We Know" in draft.body
    assert "## Sources" in draft.body
    assert "- https://example.com/press" in draft.body
    assert draft.seo_title == "Company X Announces Product Y"
    assert provider.kwargs["format"] == _WRITER_JSON_SCHEMA
    assert provider.kwargs["temperature"] == 0.4


async def test_writer_strips_fenced_json():
    fenced = f"```json\n{VALID_JSON}\n```"
    provider = FakeProvider(LLMResponse(text=fenced, model="m"))
    agent = WriterAgent(provider)
    draft = await agent.write(**BASE_KWARGS)
    assert draft.headline == "Company X Announces Product Y"


async def test_writer_retries_then_parses():
    provider = FakeProvider(
        LLMResponse(text="not json", model="m"),
        LLMResponse(text=VALID_JSON, model="m"),
    )
    agent = WriterAgent(provider)
    draft = await agent.write(**BASE_KWARGS)
    assert draft.headline == "Company X Announces Product Y"
    assert provider.calls == 2


async def test_writer_falls_back_to_template_on_llm_failure():
    provider = FakeProvider(LLMError("timeout"), LLMError("timeout"))
    agent = WriterAgent(provider)
    draft = await agent.write(**BASE_KWARGS)

    assert provider.calls == 2
    assert draft.headline == "Company X announces product Y"
    assert "Company X announced a new product." in draft.body
    assert draft.seo_title == "Company X announces product Y"


async def test_writer_fallback_includes_sources_section():
    provider = FakeProvider(LLMError("down"), LLMError("down"))
    agent = WriterAgent(provider)
    draft = await agent.write(**BASE_KWARGS)
    assert "## Sources" in draft.body
    assert "- https://example.com/announcement" in draft.body
    assert "## How We Know" in draft.body


async def test_writer_includes_claims_in_prompt():
    provider = FakeProvider(LLMResponse(text=VALID_JSON, model="m"))
    agent = WriterAgent(provider)
    await agent.write(**BASE_KWARGS)
    assert "Company X announced a new product." in provider.prompt
    assert "CONFIRMED" in provider.prompt
    assert "https://example.com/announcement" in provider.prompt


async def test_writer_empty_claims_uses_fallback_gracefully():
    provider = FakeProvider(LLMError("down"), LLMError("down"))
    agent = WriterAgent(provider)
    draft = await agent.write(title="Solo headline", summary="", category=None, claims=[], source_urls=[])
    assert draft.headline == "Solo headline"
    assert draft.body
    assert "## Sources" not in draft.body