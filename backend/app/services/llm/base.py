from __future__ import annotations

import abc
from dataclasses import dataclass


class LLMError(Exception):
    """Raised when a provider call fails (network, timeout, HTTP error)."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(abc.ABC):
    """Contract for LLM backends; agents depend on this, never on a concrete provider."""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        format: str | dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Run a single completion and return raw text plus token usage."""