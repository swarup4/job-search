"""Where the tier writes files."""

import os
from pathlib import Path

import config  # noqa: F401 — imported for its .env load

_TIER_ROOT = Path(__file__).resolve().parent.parent

TAILORED_DIR = Path(os.environ.get("TAILORED_DIR", _TIER_ROOT / "output" / "tailored"))
