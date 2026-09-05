from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openai import OpenAIProvider
from app.services.llm.anthropic import AnthropicProvider

__all__ = [
    "AnthropicProvider",
    "LLMError",
    "LLMProvider",
    "LLMResponse",
    "OllamaProvider",
    "OpenAIProvider",
    "get_provider",
]


def get_provider() -> LLMProvider:
    settings = get_settings()
    match settings.llm_provider:
        case "ollama":
            return OllamaProvider()
        case "openai":
            return OpenAIProvider()
        case "anthropic":
            return AnthropicProvider()
        case _:
            raise LLMError(f"Unknown LLM provider: {settings.llm_provider}")