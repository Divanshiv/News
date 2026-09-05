from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse


def _error_detail(response: httpx.Response) -> str:
    try:
        err = response.json().get("error") or {}
        if isinstance(err, dict) and err.get("message"):
            return err["message"][:300]
    except (ValueError, AttributeError):
        pass
    return response.text[:300]


class AnthropicProvider(LLMProvider):
    """LLMProvider backed by the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        self.base_url = (base_url or settings.anthropic_base_url).rstrip("/")
        self.model = model or settings.anthropic_model
        self._default_max_tokens = max_tokens or settings.anthropic_max_tokens
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds or settings.anthropic_timeout_seconds
        )

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        format: str | dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        body: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self._default_max_tokens,
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        if format is not None:
            body["messages"].append(
                {"role": "user", "content": "Respond ONLY with the raw JSON object. No markdown fences, no commentary."}
            )

        try:
            response = await self._client.post(
                f"{self.base_url}/v1/messages",
                json=body,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMError("Anthropic authentication failed – check ANTHROPIC_API_KEY")
        if response.status_code == 429:
            raise LLMError(f"Anthropic request throttled: {_error_detail(response)}")
        if response.status_code >= 400:
            raise LLMError(
                f"Anthropic error {response.status_code}: {_error_detail(response)}"
            )

        data = response.json()
        content_blocks = data.get("content") or []
        text = ""
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    break
        if not text:
            raise LLMError("Anthropic returned an empty response")

        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            model=data.get("model") or self.model,
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
