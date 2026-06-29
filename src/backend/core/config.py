from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at src/backend/core/ — walk up 4 levels to reach the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    database_url: str
    session_expire_hours: int = 720
    login_rate_limit: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
