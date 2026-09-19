"""Infrastructure for the AI tier: the .env load.

`.env` is read here because every entry point imports through this package, so it
happens exactly once and before anything looks at os.environ. Existing environment
variables win over the file, as they do in any twelve-factor setup.
"""

from pathlib import Path

from dotenv import load_dotenv

# Anchored to ai/.env rather than the process's cwd, so an agent run from any
# directory finds the same file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
