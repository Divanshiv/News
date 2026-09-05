from app.core.config import get_settings
from app.services.llm.base import LLMError, LLMProvider, LLMResponse
from app.services.llm.ollama import OllamaProvider

__all__ = ["LLMError", "LLMProvider", "LLMResponse", "OllamaProvider", "get_provider"]


def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return OllamaProvider()
    raise LLMError(f"Unknown LLM provider: {settings.llm_provider}")