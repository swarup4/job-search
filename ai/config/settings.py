"""The one settings loader for the AI tier. Nothing else reads the environment."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

_TIER_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_TIER_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # One OpenAI-compatible code path, two sources: moving from development to real
    # use is these three values, not a provider abstraction.
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2:latest"
    llm_timeout: float = 240.0
    # One generation plus two schema-repair retries. See NFR-2.
    llm_attempts: int = 3
    # Qwen3 reasons by default and the roadmap disables it on both sources. llama3.2
    # has no thinking mode, so this stays off until the model switch (P5-11).
    llm_disable_thinking: bool = False

    # The AI tier reaches structural data only over HTTP. It holds no database URI.
    jobpilot_api_url: str = "http://127.0.0.1:8000/api"
    jobpilot_email: str = ""
    jobpilot_password: str = ""

    tailored_dir: Path = _TIER_ROOT / "output" / "tailored"

    @property
    def llm_host(self) -> str:
        """Provenance, not routing: a score from Ollama is not comparable to a score
        from a hosted 32B, so `Match.modelName` records which produced it."""
        host = urlparse(self.llm_base_url).hostname or ""
        if host in {"127.0.0.1", "localhost", "::1"}:
            return "ollama"
        if "huggingface" in host:
            return "huggingface"
        return host or "unknown"

    @property
    def provenance(self) -> str:
        return f"{self.llm_host}/{self.llm_model}"


settings = Settings()
