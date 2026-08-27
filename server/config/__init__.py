"""Infrastructure for the server tier: the .env load, and the local MongoDB client.

`.env` is loaded here because both consumers — `config.database` and `main` — import
through this package, so it is read exactly once and before anything looks at os.environ.
Existing environment variables win over the file, as they do in any twelve-factor setup.
"""

from pathlib import Path

from dotenv import load_dotenv

# Anchored to server/.env rather than the process's cwd, so `uvicorn main:app` finds
# the same file whichever directory it is launched from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
