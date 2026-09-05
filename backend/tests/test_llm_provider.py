import json

import httpx
import pytest

from app.services.llm.base import LLMError
from app.services.llm.ollama import OllamaProvider


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


async def test_generate_posts_payload_and_parses_usage():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = _body(request)
        return httpx.Response(
            200,
            json={
                "model": "llama3.2",
                "response": '{"should_research": true}',
                "done": True,
                "prompt_eval_count": 12,
                "eval_count": 5,
            },
        )

    provider = OllamaProvider(
        base_url="http://ollama:11434",
        model="llama3.2",
        timeout_seconds=5,
        client=_client_for(handler),
    )
    try:
        response = await provider.generate(
            "Grade this story",
            system="Be strict",
            format="json",
            temperature=0.2,
            max_tokens=200,
        )
    finally:
        await provider.aclose()

    assert captured["url"] == "http://ollama:11434/api/generate"
    body = captured["payload"]
    assert body["model"] == "llama3.2"
    assert body["prompt"] == "Grade this story"
    assert body["system"] == "Be strict"
    assert body["format"] == "json"
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0.2, "num_predict": 200}
    assert response.text == '{"should_research": true}'
    assert response.model == "llama3.2"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 5


async def test_generate_omits_optional_fields():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = _body(request)
        return httpx.Response(200, json={"response": "ok"})

    provider = OllamaProvider(
        base_url="http://ollama:11434",
        client=_client_for(handler),
    )
    try:
        response = await provider.generate("hi")
    finally:
        await provider.aclose()

    body = captured["payload"]
    assert "system" not in body
    assert "format" not in body
    assert "temperature" not in body
    assert response.prompt_tokens == 0
    assert response.completion_tokens == 0


async def test_model_not_found_raises_llm_error():
    provider = OllamaProvider(
        base_url="http://ollama:11434",
        model="missing-model",
        client=_client_for(lambda req: httpx.Response(404, json={"error": "nope"})),
    )
    try:
        with pytest.raises(LLMError, match="not found"):
            await provider.generate("hi")
    finally:
        await provider.aclose()


async def test_http_error_raises_llm_error():
    provider = OllamaProvider(
        base_url="http://ollama:11434",
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

    provider = OllamaProvider(
        base_url="http://ollama:11434",
        client=_client_for(handler),
    )
    try:
        with pytest.raises(LLMError, match="connection refused"):
            await provider.generate("hi")
    finally:
        await provider.aclose()


async def test_empty_response_raises_llm_error():
    provider = OllamaProvider(
        base_url="http://ollama:11434",
        client=_client_for(lambda req: httpx.Response(200, json={"response": "   "})),
    )
    try:
        with pytest.raises(LLMError, match="empty"):
            await provider.generate("hi")
    finally:
        await provider.aclose()