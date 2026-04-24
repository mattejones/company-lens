from services.llm.base import LLMAdapter
from services.llm.openai_adapter import OpenAIAdapter
from services.llm.ollama_adapter import OllamaAdapter
from api.config import settings


def build_llm_adapter() -> LLMAdapter:
    """Factory that returns the appropriate LLM adapter based on config.

    Adding a new provider means:
    1. Create a new adapter in services/llm/
    2. Add a new elif branch here
    3. Add any new config fields to api/config.py and .env.example

    No service code needs to change.
    """
    if settings.llm_provider == "openai":
        return OpenAIAdapter(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.llm_base_url,
            reasoning_effort=settings.llm_reasoning_effort or None,
        )

    if settings.llm_provider == "ollama":
        return OllamaAdapter(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )

    raise ValueError(
        f"Unknown LLM provider: '{settings.llm_provider}'. "
        f"Supported providers: openai, ollama"
    )
