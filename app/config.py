import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Default is for local development; in production it should be overridden by environment variable
    database_url: str = "postgresql://postgres:postgres@localhost:5432/aceh_sentimen"
    environment: str = "development"
    hf_token: str = ""
    rapidapi_tiktok_key: str = ""
    gemini_api_key: str = ""

    # 9Router configuration
    ninerouter_api_base: str | None = None
    ninerouter_api_key: str | None = None
    ninerouter_model: str = "gemini-2.5-flash"



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

if settings.environment == "production" and "localhost" in settings.database_url:
    logging.warning("WARNING: Environment is set to production but DATABASE_URL points to localhost.")
