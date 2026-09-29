from __future__ import annotations

from pathlib import Path

import pytest

from config import error_log


@pytest.fixture(autouse=True)
def log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Failures the suite provokes on purpose stay out of the real `logs/errors.jsonl`."""
    path = tmp_path / "errors.jsonl"
    monkeypatch.setattr(error_log, "ERROR_LOG_PATH", path)
    return path
