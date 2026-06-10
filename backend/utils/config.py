from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

ENV_FILE_PATH = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):

    app_name: str = "TRAX-AI"
    debug: bool = False

    database_url: str
    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    gemini_api_key: str
    llm_model:str = "gemini/gemini-3.1-flash-lite"
    news_api_key: str

    sec_user_agent: str = "FinancePlatform contact@example.com"

    # Updated to Pydantic V2 syntax
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="allow", case_sensitive=False)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()