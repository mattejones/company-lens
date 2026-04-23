from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    ch_api_key: str
    openai_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
