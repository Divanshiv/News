import pytest

from app.agents.verification import VerificationAgent, _VERIFICATION_JSON_SCHEMA
from app.services.llm.base import LLMError, LLMResponse

VALID_JSON = (
    '{"claims": [{"claim_id": 1, "status": "CONFIRMED", "confidence": 0.9, '
    '"reasoning": "Supported by official announcement.", '
    '"supporting_sources": ["https://example.com"], "contradicting_sources": []}], '
    '"overall_confidence": 0.9, "summary": "Claim verified."}'
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
        "evidence_urls": ["https://example.com/announcement"],
        "evidence_texts": ["Company X today announced Product Y."],
    }
]


async def test_verification_parses_valid_json():
    provider = FakeProvider(LLMResponse(text=VALID_JSON, model="m"))
    agent = VerificationAgent(provider)
    result = await agent.verify(story_id=1, claims=SAMPLE_CLAIMS)

    assert result.story_id == 1
    assert len(result.claims) == 1
    assert result.claims[0].status == "CONFIRMED"
    assert result.claims[0].confidence == 0.9
    assert result.overall_confidence == 0.9
    assert provider.kwargs["format"] == _VERIFICATION_JSON_SCHEMA
    assert provider.kwargs["temperature"] == 0.1


async def test_verification_strips_fenced_json():
    fenced = f"```json\n{VALID_JSON}\n```"
    provider = FakeProvider(LLMResponse(text=fenced, model="m"))
    agent = VerificationAgent(provider)
    result = await agent.verify(story_id=1, claims=SAMPLE_CLAIMS)
    assert result.claims[0].status == "CONFIRMED"


async def test_verification_retries_then_parses():
    provider = FakeProvider(
        LLMResponse(text="not json", model="m"),
        LLMResponse(text=VALID_JSON, model="m"),
    )
    agent = VerificationAgent(provider)
    result = await agent.verify(story_id=1, claims=SAMPLE_CLAIMS)
    assert result.claims[0].status == "CONFIRMED"
    assert provider.calls == 2


async def test_verification_falls_back_to_heuristic_on_llm_failure():
    provider = FakeProvider(LLMError("timeout"), LLMError("timeout"))
    agent = VerificationAgent(provider)
    result = await agent.verify(story_id=1, claims=SAMPLE_CLAIMS)

    assert provider.calls == 2
    assert len(result.claims) == 1
    assert result.claims[0].status in ("CONFIRMED", "LIKELY", "UNCONFIRMED", "CONTRADICTED")
    assert "Rule-based" in result.claims[0].reasoning


async def test_verification_empty_claims():
    provider = FakeProvider()
    agent = VerificationAgent(provider)
    result = await agent.verify(story_id=1, claims=[])
    assert result.claims == []
    assert result.overall_confidence == 0.0
    assert provider.calls == 0


async def test_heuristic_verification_with_confirmation_indicators():
    provider = FakeProvider(LLMError("down"), LLMError("down"))
    agent = VerificationAgent(provider)
    claims = [
        {
            "claim_id": 1,
            "claim_text": "Company X announced a new product.",
            "evidence_urls": ["https://a.com", "https://b.com"],
            "evidence_texts": [
                "Company X confirmed the launch today.",
                "According to the official statement, the product is verified.",
            ],
        }
    ]
    result = await agent.verify(story_id=1, claims=claims)
    assert result.claims[0].status == "CONFIRMED"
    assert result.claims[0].confidence == 0.7


async def test_heuristic_verification_with_contradiction_indicators():
    provider = FakeProvider(LLMError("down"), LLMError("down"))
    agent = VerificationAgent(provider)
    claims = [
        {
            "claim_id": 1,
            "claim_text": "Product X is safe.",
            "evidence_urls": ["https://a.com"],
            "evidence_texts": [
                "The claim was refuted by experts. The product is misleading and inaccurate.",
            ],
        }
    ]
    result = await agent.verify(story_id=1, claims=claims)
    assert result.claims[0].status == "CONTRADICTED"
