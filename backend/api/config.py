from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str
    redis_url: str
    ch_api_key: str

    # LLM
    llm_provider: str = "openai"        # openai | ollama
    llm_model: str = "gpt-4o"
    llm_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""


settings = Settings()
