import json

import httpx
import pytest

from app.services.llm.anthropic import AnthropicProvider
from app.services.llm.base import LLMError


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


async def test_generate_posts_payload_and_parses_usage():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = _body(request)
        return httpx.Response(
            200,
            json={
                "model": "claude-sonnet-4-20250514",
                "content": [{"type": "text", "text": '{"should_research": true}'}],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            },
        )

    provider = AnthropicProvider(
        api_key="test-key",
        model="claude-sonnet-4-20250514",
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

    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    body = captured["payload"]
    assert body["model"] == "claude-sonnet-4-20250514"
    assert body["system"] == "Be strict"
    assert body["max_tokens"] == 200
    assert body["temperature"] == 0.2
    assert response.text == '{"should_research": true}'
    assert response.model == "claude-sonnet-4-20250514"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 5


async def test_generate_uses_default_max_tokens_and_omits_optionals():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = _body(request)
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "ok"}]},
        )

    provider = AnthropicProvider(
        api_key="test-key",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        client=_client_for(handler),
    )
    try:
        response = await provider.generate("hi")
    finally:
        await provider.aclose()

    body = captured["payload"]
    assert body["max_tokens"] == 4096
    assert "system" not in body
    assert "temperature" not in body
    assert len(body["messages"]) == 1
    assert response.prompt_tokens == 0
    assert response.completion_tokens == 0


async def test_missing_api_key_raises_llm_error():
    with pytest.raises(LLMError, match="API_KEY"):
        AnthropicProvider(
            api_key="",
            client=_client_for(lambda req: httpx.Response(200, json={"content": []})),
        )


async def test_http_error_raises_llm_error():
    provider = AnthropicProvider(
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

    provider = AnthropicProvider(
        api_key="test-key",
        client=_client_for(handler),
    )
    try:
        with pytest.raises(LLMError, match="connection refused"):
            await provider.generate("hi")
    finally:
        await provider.aclose()


async def test_empty_response_raises_llm_error():
    provider = AnthropicProvider(
        api_key="test-key",
        client=_client_for(lambda req: httpx.Response(200, json={"content": []})),
    )
    try:
        with pytest.raises(LLMError, match="empty"):
            await provider.generate("hi")
    finally:
        await provider.aclose()
