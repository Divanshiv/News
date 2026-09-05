from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse


def _throttle_reason(response: httpx.Response) -> str:
    try:
        err = response.json().get("error") or {}
        code = err.get("code") or err.get("type") or "rate_limit"
        return f" ({code})"
    except (ValueError, AttributeError):
        return ""


class OpenAIProvider(LLMProvider):
    """LLMProvider backed by OpenAI's Chat Completions API (also works with
    any OpenAI-compatible endpoint, e.g. Azure OpenAI or a local proxy)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.model = model or settings.openai_model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds or settings.openai_timeout_seconds
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
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_completion_tokens"] = max_tokens
        if format is not None:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMError("OpenAI authentication failed – check OPENAI_API_KEY")
        if response.status_code == 429:
            raise LLMError(f"OpenAI request throttled{_throttle_reason(response)}")
        if response.status_code >= 400:
            raise LLMError(
                f"OpenAI error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") or "").strip()
        if not text:
            raise LLMError("OpenAI returned an empty response")

        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            model=data.get("model") or self.model,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
