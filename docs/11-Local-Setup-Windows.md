# 11 — Local setup on Windows

The README and [doc 07](07-PDF-Setup-macOS.md) assume macOS. This is the same setup on Windows
(roadmap `P13-08`), rewritten on 2026-11-18 for the open-source stack in
[roadmap Phase 13](../05-Roadmap-Backlog.md#14-phase-13--local-open-source-stack). Commands are for Git Bash or PowerShell.

Everything runs on this machine. There is no account to create and no key to obtain.

## 1. Tools

| Tool | Needed for | Install |
|---|---|---|
| Python 3.12+ | `server/` and `ai/` (both refuse 3.11 and older) | `uv python install 3.12` |
| [uv](https://docs.astral.sh/uv/) | Python dependencies | already present if `uv --version` answers |
| Node 18+ | `app/web`, `app/extension` | nodejs.org |
| MongoDB Community Server | the application database and the server test suite | mongodb.com/try/download/community, default port 27017 |
| [Ollama](https://ollama.com/download) | the generation model and the embedding model | ollama.com/download |
| MiKTeX or TeX Live | PDF download only | miktex.org, then set `PDFLATEX_BIN` |

Three things that are easy to trip over:

- **Any MongoDB works.** Vector search is an exact cosine computed in the server, so a local
  Community Server does everything. The app and the test suite can share one instance: the
  suite uses its own database, `jobpilot_test`, and drops it afterwards.
- **If another virtual environment is active**, uv warns that `VIRTUAL_ENV` does not match and
  may pick the wrong interpreter. Deactivate it first, or run `unset VIRTUAL_ENV` (Git Bash) /
  `Remove-Item Env:VIRTUAL_ENV` (PowerShell).
- **`ollama list` starts Ollama's background server** if it is not running, and can take a
  while to answer the first time.

## 2. Models

Two models, both pulled into Ollama:

```bash
ollama pull bge-m3          # embeddings, 1,024 dimensions, about 1.2 GB
ollama pull qwen3.5:9b      # generation: the code default
```

**Choose the generation model once and keep it.** Scores from different models are not
comparable, and every baseline is tied to the model it was taken on. It must be open-weights,
must honour a strict JSON schema, and must fit this machine's memory. A small model such as
`phi3` will not hold the schemas.

The code expects a 16,384-token context window. `LLM_NUM_CTX` must equal `num_ctx` in the
model's Modelfile, because Ollama ignores a per-request size on its OpenAI-compatible API.

Check the embedding model answers, and see where the near-miss threshold sits for it:

```bash
cd ai && uv run python -m rag.embeddings
```

## 3. Install

```bash
cd server && uv sync --frozen --python 3.12
cd ../ai && uv sync --frozen --python 3.12
cd ../app/web && npm install
cd ../extension && npm install
```

## 4. Configure

Copy each `.env.example` to `.env` (`.env.local` for `app/web`) and set:

| File | Set |
|---|---|
| `server/.env` | `JWT_SECRET` (a random string of at least 32 bytes; the server refuses to start without one), `PDFLATEX_BIN` (full path to `pdflatex.exe`, for PDF download) |
| `ai/.env` | `LLM_MODEL`, if you chose a model other than the default. Nothing else is required |

`MONGODB_URI` already points at `mongodb://127.0.0.1:27017`, and both model endpoints already
point at Ollama on this machine.

## 5. Coming from the earlier, hosted setup

Skip this on a new, empty database.

- **Vectors.** Chunks embedded by the previous hosted model are embedded again automatically
  on the next scoring run: each chunk records the model that embedded it, and a search only
  uses chunks from its own model. Nothing has to be cleared by hand.
- **Indexes.** A database created before 2026-11-10 has unique indexes that let only one
  account score or tailor a given job. Run once, before starting the server on the new code:

  ```bash
  cd server
  uv run python migrate_per_user_indexes.py            # dry run
  uv run python migrate_per_user_indexes.py --apply
  ```

- **Search indexes.** The two Atlas search indexes are no longer read. They can be left or
  deleted.

## 6. Run

Start MongoDB and Ollama, then three terminals, API server first:

```bash
cd server && uv run python main.py          # http://127.0.0.1:8000/docs
cd ai && uv run python main.py              # http://127.0.0.1:8001/docs
cd app/web && npm run dev                   # http://localhost:3000
```

Extension: `cd app/extension && npm run build`, then load `app/extension/dist` unpacked from
`chrome://extensions` with Developer mode on.

Settings → **Models & privacy** shows which models the AI tier is using and marks each one
"local" or "not local".

## 7. Test

```bash
cd ai && uv run pytest            # model and API are faked; no services needed
cd ai && uv run pytest -m llm     # the live tests: needs the generation model in Ollama
cd server && uv run pytest        # needs MongoDB on 127.0.0.1:27017
```

`TEST_MONGODB_URI` points the server suite at a different instance. It creates and drops a
database named `jobpilot_test`, so never point it at a database you share.

## 8. Record a usage baseline

Every model call is written to the `llm_usage` collection when a run ends. To record the
baseline the plan asks for (`EV-00`):

1. Sign in, add a profile, and run discovery until about 50 jobs are stored.
2. Start a scoring run from the header's Refresh, and let it finish. It scores at most
   `SCORING_MAX_JOBS` jobs (default 50) inside your saved Search targets. Note the run id from
   the `run_started` event or the AI tier's log line `scoring run <id>`.
3. Read the totals per step:

```bash
curl -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/api/llm-usage/summary?runId=<run id>"
```

Each row is one step under one model and prompt version, with calls, retries, prompt tokens,
cached tokens, completion tokens and average time. Save the output with the model names and
the machine it ran on: on a local model, time depends on the hardware.
