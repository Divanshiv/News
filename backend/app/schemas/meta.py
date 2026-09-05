"""Public, non-secret service configuration surfaced to the operator console."""

from pydantic import BaseModel


class ServiceConfigRead(BaseModel):
    app_name: str
    app_version: str
    environment: str
    llm_provider: str
    ollama_url: str
    ollama_model: str
    openai_model: str | None = None
    anthropic_model: str | None = None
