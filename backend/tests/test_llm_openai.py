import json

import httpx
import pytest

from app.services.llm.base import LLMError
from app.services.llm.openai import OpenAIProvider


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


async def test_generate_posts_payload_and_parses_usage():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = _body(request)
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "model": "gpt-5-mini",
                "choices": [
                    {"message": {"content": '{"should_research": true}'}}
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 5},
            },
        )

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-5-mini",
        timeout_seconds=5,
        client=_client_for(handler),
    )
    try:
        response = await provider.generate(
            "Grade this story",
            system="Be strict",
            format={"type": "object"},
            temperature=0.2,
            max_tokens=200,
        )
    finally:
        await provider.aclose()

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer test-key"
    body = captured["payload"]
    assert body["model"] == "gpt-5-mini"
    assert body["messages"] == [
        {"role": "system", "content": "Be strict"},
        {"role": "user", "content": "Grade this story"},
    ]
    assert body["temperature"] == 0.2
    assert body["max_completion_tokens"] == 200
    assert body["response_format"] == {"type": "json_object"}
    assert response.text == '{"should_research": true}'
    assert response.model == "gpt-5-mini"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 5


async def test_generate_omits_optional_fields():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = _body(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = OpenAIProvider(
        api_key="test-key",
        client=_client_for(handler),
    )
    try:
        response = await provider.generate("hi")
    finally:
        await provider.aclose()

    body = captured["payload"]
    assert "system" not in body["messages"][0]
    assert len(body["messages"]) == 1
    assert "temperature" not in body
    assert "max_completion_tokens" not in body
    assert "response_format" not in body
    assert response.prompt_tokens == 0
    assert response.completion_tokens == 0


async def test_missing_api_key_raises_llm_error():
    with pytest.raises(LLMError, match="API_KEY"):
        OpenAIProvider(
            api_key="",
            client=_client_for(lambda req: httpx.Response(200, json={"choices": []})),
        )


async def test_http_error_raises_llm_error():
    provider = OpenAIProvider(
        api_key="test-key",
        client=_client_for(lambda req: httpx.Response(500, text="boom")),
    )
    try:
        with pytest.raises(LLMError, match="500"):
            await provider.generate("hi")
    finally:
        await provider.aclose()


async def test_connection_error_raises_llm_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = OpenAIProvider(
        api_key="test-key",
        client=_client_for(handler),
    )
    try:
        with pytest.raises(LLMError, match="connection refused"):
            await provider.generate("hi")
    finally:
        await provider.aclose()


async def test_empty_response_raises_llm_error():
    provider = OpenAIProvider(
        api_key="test-key",
        client=_client_for(
            lambda req: httpx.Response(
                200, json={"choices": [{"message": {"content": "   "}}]}
            )
        ),
    )
    try:
        with pytest.raises(LLMError, match="empty"):
            await provider.generate("hi")
    finally:
        await provider.aclose()
