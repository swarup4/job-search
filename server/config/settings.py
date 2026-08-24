from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_local_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db_name: str = "jobpilot"

    host: str = "127.0.0.1"
    port: int = 8000

    web_origin: str = "http://localhost:3000"
    extension_origin: str = "chrome-extension://"

    redis_url: str = "redis://127.0.0.1:6379/0"
    resume_output_dir: str = "~/jobpilot/resumes"

    # NFR-7 / FR-5.3. Not a setting, a constant kept here so nothing has to
    # invent its own answer.
    auto_submit_enabled: bool = Field(default=False, frozen=True)

    @property
    def cors_origins(self) -> list[str]:
        return [self.web_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
