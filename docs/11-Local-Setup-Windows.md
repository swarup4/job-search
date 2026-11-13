# 11 — Local setup on Windows

The README and [doc 07](07-PDF-Setup-macOS.md) assume macOS. This is the same setup on Windows,
as worked through on 2026-11-10 (plan task `LS-06`). Commands are for Git Bash or PowerShell.

## 1. Tools

| Tool | Needed for | Install |
|---|---|---|
| Python 3.12+ | `server/` and `ai/` (both refuse 3.11 and older) | `uv python install 3.12` |
| [uv](https://docs.astral.sh/uv/) | Python dependencies | already present if `uv --version` answers |
| Node 18+ | `app/web`, `app/extension` | nodejs.org |
| MongoDB Atlas cluster | the application database | free M0 tier at mongodb.com/atlas |
| Local MongoDB | the server test suite only | MongoDB Community Server, default port 27017 |
| MiKTeX or TeX Live | PDF download only | miktex.org, then set `PDFLATEX_BIN` |
| Voyage API key | embeddings for near-miss hints | dash.voyageai.com |

Two things that are easy to trip over:

- **Atlas is required even for local use.** The near-miss search uses `$vectorSearch`, which a
  local MongoDB does not have, so scoring a job with any missing requirement fails on a local
  database. Use Atlas for the app and a local MongoDB only for `server/tests`.
- **If another virtual environment is active**, uv warns that `VIRTUAL_ENV` does not match and
  may pick the wrong interpreter. Deactivate it first, or run `unset VIRTUAL_ENV` (Git Bash) /
  `Remove-Item Env:VIRTUAL_ENV` (PowerShell).

## 2. Install

```bash
cd server && uv sync --frozen --python 3.12
cd ../ai && uv sync --frozen --python 3.12
cd ../app/web && npm install
cd ../extension && npm install
```

## 3. Configure

Copy each `.env.example` to `.env` (`.env.local` for `app/web`) and set:

| File | Set |
|---|---|
| `server/.env` | `MONGODB_URI` (your Atlas connection string), `JWT_SECRET` (long random string), `PDFLATEX_BIN` (full path to `pdflatex.exe`) |
| `ai/.env` | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `VOYAGE_API_KEY` |

**Choose the model once and keep it.** Scores from different models are not comparable.

- *Local:* Ollama at `http://localhost:11434/v1`. The code default is `qwen3.5:9b` with a
  16,384-token window, and `LLM_NUM_CTX` must match `num_ctx` in the model's Modelfile because
  Ollama ignores a per-request size on this endpoint. Pull the model first; a small model such as
  `phi3` will not hold the JSON schemas.
- *Hosted:* the values in `ai/.env.example` point at a hosted router. Every posting and profile
  line in a prompt then leaves the machine. One test,
  `test_no_hosted_llm_endpoint_appears_in_code_or_env_templates`, fails for as long as the
  template names a hosted endpoint.

## 4. Existing database only: replace two indexes

A database created before 2026-11-10 has unique indexes that let only one account score or tailor
a given job. Run once, before starting the server on the new code:

```bash
cd server
uv run python migrate_per_user_indexes.py            # dry run
uv run python migrate_per_user_indexes.py --apply
```

A new, empty database does not need this.

## 5. Run

Three terminals, API server first:

```bash
cd server && uv run python main.py          # http://127.0.0.1:8000/docs
cd ai && uv run python main.py              # http://127.0.0.1:8001/docs
cd app/web && npm run dev                   # http://localhost:3000
```

Extension: `cd app/extension && npm run build`, then load `app/extension/dist` unpacked from
`chrome://extensions` with Developer mode on.

## 6. Test

```bash
cd ai && uv run pytest            # model and API are faked; no services needed
cd server && uv run pytest        # needs a local MongoDB on 127.0.0.1:27017
```

`TEST_MONGODB_URI` points the server suite at a different local instance. It creates and drops a
database named `jobpilot_test`, so never point it at Atlas.

## 7. Record a usage baseline

Every model call is now written to the `llm_usage` collection when a run ends. To record the
baseline the plan asks for (`EV-00`):

1. Sign in, add a profile, and run discovery until about 50 jobs are stored.
2. Start a scoring run from the header's Refresh, and let it finish. Note the run id from the
   `run_started` event or the AI tier's log line `scoring run <id>`.
3. Read the totals per step:

```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/llm-usage/summary?runId=<run id>"
```

Each row is one step under one model and prompt version, with calls, retries, prompt tokens,
cached tokens, completion tokens and average time. Save the output; the prompt changes in plan
step `A3` are judged against it.
