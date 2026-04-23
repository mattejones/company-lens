from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str
    redis_url: str
    ch_api_key: str
    openai_api_key: str


settings = Settings()
