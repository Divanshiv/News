import pytest

from app.agents.scout import ScoutAgent, _SCOUT_JSON_SCHEMA, _SYSTEM_PROMPT
from app.services.llm.base import LLMError, LLMResponse

VALID_JSON = (
    '{"should_research": true, "importance": 7, '
    '"category": "AI", "reason": "Significant model release."}'
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


async def test_scout_parses_valid_json():
    provider = FakeProvider(LLMResponse(text=VALID_JSON, model="m"))
    verdict = await ScoutAgent(provider).scout(
        title="OpenAI launches new model",
        summary="The lab shipped a frontier release today.",
        category_hint="AI",
    )

    assert verdict.should_research is True
    assert verdict.importance == 7
    assert verdict.category == "AI"
    assert "Significant" in verdict.reason
    assert provider.kwargs["format"] == _SCOUT_JSON_SCHEMA
    assert provider.kwargs["temperature"] == 0.2
    assert _SYSTEM_PROMPT in provider.kwargs["system"]
    assert "OpenAI launches new model" in provider.prompt


async def test_scout_strips_fenced_and_prose_wrapped_json():
    fenced = f"```json\n{VALID_JSON}\n```"
    assert (await ScoutAgent(FakeProvider(LLMResponse(text=fenced, model="m"))).scout(
        title="t"
    )).should_research is True

    wrapped = f"Here you go:\n{VALID_JSON}\nEnjoy!"
    assert (await ScoutAgent(FakeProvider(LLMResponse(text=wrapped, model="m"))).scout(
        title="t"
    )).should_research is True


async def test_scout_coerces_category_case_and_hint_fallback():
    provider = FakeProvider(
        LLMResponse(
            text='{"should_research": false, "importance": 2, "category": "cybersecurity", "reason": "Minor."}',
            model="m",
        )
    )
    verdict = await ScoutAgent(provider).scout(title="t")
    assert verdict.category == "Cybersecurity"

    provider = FakeProvider(
        LLMResponse(
            text='{"should_research": false, "importance": 2, "category": "Nonsense", "reason": "Minor."}',
            model="m",
        )
    )
    verdict = await ScoutAgent(provider).scout(title="t", category_hint="Space")
    assert verdict.category == "Space"


async def test_scout_retries_then_parses():
    provider = FakeProvider(
        LLMResponse(text="this is not json at all", model="m"),
        LLMResponse(text=VALID_JSON, model="m"),
    )
    verdict = await ScoutAgent(provider).scout(title="t")
    assert verdict.importance == 7
    assert provider.calls == 2


async def test_scout_retries_on_out_of_range_importance():
    provider = FakeProvider(
        LLMResponse(
            text='{"should_research": true, "importance": 15, "category": "AI", "reason": "X."}',
            model="m",
        ),
        LLMResponse(text=VALID_JSON, model="m"),
    )
    verdict = await ScoutAgent(provider).scout(title="t")
    assert verdict.importance == 7
    assert provider.calls == 2


async def test_scout_falls_back_to_rules_after_repeated_llm_failures():
    provider = FakeProvider(
        LLMError("timeout"), LLMError("timeout")
    )
    verdict = await ScoutAgent(provider).scout(
        title="Startup raises $50M funding round",
        summary="Series B led by existing investors.",
    )
    assert provider.calls == 2
    assert verdict.should_research is True
    assert verdict.importance == 8
    assert verdict.category == "Business"
    assert "Rule-based" in verdict.reason


async def test_rules_fallback_low_importance():
    verdict = await ScoutAgent(FakeProvider(LLMError("down"), LLMError("down"))).scout(
        title="Weekly community newsletter"
    )
    assert verdict.should_research is False
    assert verdict.importance == 4
    assert verdict.category == "Technology"


async def test_rules_fallback_keeps_valid_category_hint():
    verdict = await ScoutAgent(FakeProvider(LLMError("down"), LLMError("down"))).scout(
        title="Rocket launches from cape",
        category_hint="Space",
    )
    assert verdict.category == "Space"