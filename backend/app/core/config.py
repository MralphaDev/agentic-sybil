from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: agentic-sybil/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str
    HELIUS_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
