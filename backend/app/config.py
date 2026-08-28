from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    app_name: str = "WeatherGPT API"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    request_timeout_seconds: float = 10.0
    cors_origins: list[str] = ["http://localhost:5173"]
    llm_api_key: str | None = None
    llm_provider: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()