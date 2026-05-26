from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ABA_",
        extra="ignore",
    )

    app_name: str = "Autonomous Browser Agent"
    environment: str = "local"
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("data"))
    logs_dir: Path = Field(default=Path("logs"))
    sqlite_path: Path = Field(default=Path("data/agent.sqlite3"))
    ollama_base_url: str = "http://localhost:11434"
    default_planner_model: str = "gemma4"
    default_coder_model: str = "qwen2.5-coder"
    browser_headless: bool = False
    browser_action_timeout_seconds: float = 20.0
    run_timeout_seconds: float = 900.0
    max_step_attempts: int = 3

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

