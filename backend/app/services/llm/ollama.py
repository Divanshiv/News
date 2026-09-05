from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """LLMProvider backed by a local Ollama server over its REST API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.ollama_model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds or settings.ollama_timeout_seconds
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
        options: dict[str, object] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        payload: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        try:
            response = await self._client.post(
                f"{self.base_url}/api/generate", json=payload
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        if response.status_code == 404:
            raise LLMError(f"Ollama model not found: {self.model!r}")
        if response.status_code >= 400:
            raise LLMError(
                f"Ollama error {response.status_code}: {response.text[:200]}"
            )
        data = response.json()
        text = (data.get("response") or "").strip()
        if not text:
            raise LLMError("Ollama returned an empty response")
        return LLMResponse(
            text=text,
            model=data.get("model") or self.model,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            completion_tokens=int(data.get("eval_count") or 0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()