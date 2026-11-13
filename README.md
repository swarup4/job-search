# JobPilot

**A personal, single-user job-search co-pilot. Generation runs on a local model; you approve every
change to your resume and press every Submit button yourself.**

JobPilot pulls job postings from company career pages and from pages you capture in the browser,
scores each one against your profile, tailors your resume with only the keywords you approve, and
fills application forms in your own browser session.

> ⚠️ **Personal project.** Built for one person on one machine. Everything binds to `127.0.0.1`;
> nothing here is meant to be exposed publicly.

---

## Table of Contents

- [Current state](#current-state)
- [Features](#features)
- [Architecture](#architecture)
- [What leaves your machine](#what-leaves-your-machine)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Tests](#tests)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Design Principles](#design-principles)
- [License](#license)

---

## Current state

*Updated 2026-11-10.* The application works end to end by hand. The agentic layer (LangGraph
agents, MCP tool servers, scheduling, evaluation) is not built yet: every AI step today is a plain
function called from an API endpoint.

| Area | Status |
|---|---|
| **Dashboard** (`app/web`) | **Built and wired.** 13 screens on the live API — pipeline board, search, shortlist, job details, keyword selection, tailored resume preview, resume, applications, my details, settings, login, signup. No screen reads a fixture. The resume chat panel is laid out but inert |
| **REST API** (`server`) | **Built.** 16 modules, 80 endpoints, 19 collections, Beanie over MongoDB. JWT auth on every route except signup, login and refresh |
| **AI tier** (`ai`) | **Built, without agents.** Its own FastAPI server on `:8001` runs discovery, capture parsing, analysis, scoring and tailoring as background runs that stream progress over server-sent events |
| **Job discovery** | **Workday only.** 41 companies registered (33 enabled), scraped from their public Workday feeds with no LLM. Every other platform is planned — roadmap Phase 12 |
| **Matching** | **Built.** Each posting is read once into a brief, the profile once into a skill inventory, and a score is one comparison between them. Every "you have this" is traced to a line of your profile |
| **RAG** | **Built.** Profile chunks embedded with Voyage, `$vectorSearch` then Voyage rerank, used for near-miss hints |
| **Resume** | **Built.** Six LaTeX templates rendered from your profile; `.tex` and PDF download; a tailored `.tex` per job using only the keywords you ticked |
| **Chrome extension** (`app/extension`) | **Built.** Fills Workday, Greenhouse, Lever and LinkedIn Easy Apply forms, highlights every field it touched, captures any career page into a job. No LLM fallback for unclear fields yet |
| **Agents, MCP servers, scheduler, Ragas** | **Not started** — roadmap Phases 7, 8 and 10 |
| **Tests** | 155 in `server/`, 270 in `ai/`. One `ai/` guardrail test fails today: `ai/.env.example` still names a hosted LLM router |

---

## Features

**Working today**

- 🔍 **Career-page discovery** — pulls postings straight from Workday career sites, filtered by your
  saved target roles, skills and locations before anything is written. robots.txt is checked on
  every request
- 📥 **One-click capture** — the extension saves the page you are looking at; the AI tier reads it
  into a job, refusing any title, company or figure that is not on the page
- 🎯 **Match scoring with evidence** — requirements extracted from the posting, compared against
  your profile, each "present" backed by a quote from it. Risk flags (seniority, years, location)
  are shown, never selectable
- 💡 **Near-miss hints** — when the posting says "agentic orchestration" and your profile says
  "LangGraph multi-agent pipeline", the keyword stays Missing but you are told you may already have it
- ✅ **Keyword selection** — nothing is pre-checked. Only what you tick can reach the resume, and the
  server refuses a resume built on anything else
- 📄 **Tailored resume** — the model only decides *where* a ticked keyword goes; a rewrite that adds
  any word beyond the keyword and plain connectives is declined. `.tex` and PDF download
- 🧩 **Form autofill** — fills known fields from your profile and answer bank, outlines every filled
  field green and every unanswered one amber, and never submits
- 📊 **Pipeline** — Kanban board, shortlist and Applications screen, per account

**Planned** — see the [roadmap](05-Roadmap-Backlog.md): more job sources (Indeed, SerpAPI,
LinkedIn, Naukri and ten more career-page platforms), a daily schedule, LangGraph agents with
approval interrupts, follow-up drafts, Google Sheets sync, and a Ragas faithfulness suite.

---

## Architecture

Three processes and one database:

```
   app/web (:3000)            app/extension
        │      │                    │      │
        │      └─────── HTTP ───────┼──────┼──▶  ai (:8001)
        │                           │      │      discovery · capture · analysis
        │                           │      │      scoring · tailoring
        └──────────── HTTP ─────────┴──────┴──▶  server (:8000)  ──▶  MongoDB
                                                    ▲                (Atlas, with $vectorSearch)
                                     ai ── HTTP ────┘
```

| Service | Runs | Owns |
|---|---|---|
| `app/web` | Next.js dashboard | nothing — a pure client |
| `server` | FastAPI REST API | **the database** — every collection |
| `ai` | FastAPI server for background runs; LLM calls, Voyage, scraping | no database and no credentials |

- **`server` is the only process with a database connection.** `ai` reads and writes everything
  through `server`'s REST API (`ai/mcp_servers/jobpilot_api/client.py`), acting with the signed-in
  user's forwarded token. It holds no URI and no secret of its own beyond its API keys.
- **One store.** Structural data, job-description text and profile chunks with their vectors all
  live in one MongoDB database. Pointed at Atlas (`mongodb+srv://`), the server creates the two
  `$vectorSearch` indexes on startup; pointed at a local `mongod`, everything works except vector
  search. *This replaced the earlier local-plus-Atlas split on 2026-09-19 — roadmap Phase 6.*
- **The tiers never import each other.** They talk over HTTP only.
- **Background runs stream.** `POST /api/runs/{discovery|analysis|scoring}/start` begins one run per
  account; `GET …/events` streams its progress as server-sent events, replaying from the start so a
  late page can join.

### How a job flows through it

```
discovery (Workday feed) ─┐
capture (extension)  ─────┴─▶ job + description ─▶ analyze: details · embedding · tech stack
                                                         │
                                                         ▼
                              score: brief × skill inventory ─▶ Present / Missing / risks
                                                         │
                                                         ▼
                              ⚠ you tick keywords ─▶ tailor .tex ─▶ ⚠ you review ─▶ extension fills
                                                                                    ─▶ ⚠ you submit
```

---

## What leaves your machine

| | Where it goes |
|---|---|
| Every LLM call — parsing, extraction, scoring, tailoring | **local Ollama** by default (`LLM_BASE_URL`) |
| Profile chunk text, JD text, keyword labels, when embedded or reranked | **Voyage AI** (hosted) |
| Your data at rest | **MongoDB Atlas**, when `MONGODB_URI` points there |
| Career-page requests | the companies' own public job feeds |

Pointing `LLM_BASE_URL` at a hosted provider is possible and sends every JD, profile line and
resume line in a prompt off the machine. The guardrail suite (`ai/tests/test_guardrails.py`) fails
if a hosted endpoint appears in code or an env template.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Generation | [Ollama](https://ollama.com/) over its OpenAI-compatible API; default `qwen3.5:9b`. Every call is schema-constrained (`strict` JSON Schema) and validated with Pydantic |
| Embeddings + reranking | [Voyage AI](https://www.voyageai.com/) — `voyage-4-lite` (1024 dims), `rerank-2.5-lite` |
| Database | [MongoDB](https://www.mongodb.com/) via [Beanie](https://beanie-odm.dev/) 2 / pymongo async; Atlas for `$vectorSearch` |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) ×2 (`server`, `ai`), Python 3.12, [uv](https://docs.astral.sh/uv/) |
| Auth | argon2 password hashes, JWT access + refresh tokens |
| Frontend | [Next.js](https://nextjs.org/) App Router (JavaScript), Redux, axios, Formik + Yup |
| UI | [Tailwind CSS](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/), one SCSS stylesheet |
| Scraping | `httpx` with a robots.txt-checking fetcher; `markdownify` for JDs |
| Resume | `{{TOKEN}}` substitution into uploaded `.tex` templates; **pdflatex** for PDF |
| Extension | Chrome Manifest V3, TypeScript, esbuild, `turndown` |
| Planned | LangGraph, MCP servers, Redis + Celery, Ragas, Langfuse/Phoenix |

---

## Getting Started

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 18+ and npm
- MongoDB — a free [Atlas](https://www.mongodb.com/cloud/atlas/register) M0 cluster for vector
  search, or a local `mongod` (everything but vector search works)
- [Ollama](https://ollama.com/download) with the chat model pulled:
  ```bash
  ollama pull qwen3.5:9b
  ```
  Set the model's context window (`num_ctx` in its Modelfile) to match `LLM_NUM_CTX`, default
  16384 — Ollama ignores a per-request size on its OpenAI endpoint
- A [Voyage AI](https://www.voyageai.com/) API key
- Google Chrome, for the extension
- *Optional:* a TeX engine for PDF downloads — see [docs/07](docs/07-PDF-Setup-macOS.md). Without
  it the PDF endpoint answers 503 and everything else works

### Install and run

Each tier has its own virtual environment. Run each in its own terminal, and deactivate any active
venv first or `uv` installs into it.

```bash
# 1. REST API — start this first
cd server && cp .env.example .env     # set MONGODB_URI and JWT_SECRET
uv sync && .venv/bin/python main.py   # http://127.0.0.1:8000/docs

# 2. AI tier
cd ai && cp .env.example .env         # set VOYAGE_API_KEY; check LLM_BASE_URL is local
uv sync && .venv/bin/python main.py   # http://127.0.0.1:8001/docs

# 3. Dashboard
cd app/web && npm install && npm run dev   # http://localhost:3000

# 4. Chrome extension
cd app/extension && npm install && npm run build
```

Then load the extension: `chrome://extensions` → **Developer mode** → **Load unpacked** →
`app/extension/dist`, and sign in from its popup.

### One-time data setup

```bash
cd server
.venv/bin/python seed_career_sources.py    # the 41 Workday companies
.venv/bin/python import_templates.py       # the six resume templates
```

Open the dashboard, sign up (signup signs you in), and fill in **My Details** — that profile is
what every score and every tailored resume is built from.

---

## Configuration

Values below are the defaults in code; an absent `.env` boots against them.

**`server/.env`**

| Key | Default | |
|---|---|---|
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` | `mongodb+srv://…` for Atlas and vector search |
| `MONGODB_DB_NAME` | `jobpilot` | |
| `JWT_SECRET` | — | **required**, at least 32 bytes; the server refuses to start without one. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_TTL_MINUTES` / `JWT_REFRESH_TTL_DAYS` | 60 / 30 | |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | keep loopback |
| `PDFLATEX_BIN` / `PDFLATEX_TIMEOUT_SECONDS` | `pdflatex` | |
| `LOG_LEVEL` | | |

**`ai/.env`**

| Key | Default | |
|---|---|---|
| `JOBPILOT_API_URL` | `http://127.0.0.1:8000/api` | the server |
| `AI_HOST` / `AI_PORT` | `127.0.0.1` / `8001` | |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama's OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen3.5:9b` | |
| `LLM_NUM_CTX` | `16384` | must match the model's `num_ctx` |
| `LLM_DISABLE_THINKING` | off | turn on for Qwen3-family models |
| `LLM_TIMEOUT` / `LLM_ATTEMPTS` | `240` / `3` | one try plus two schema-repair retries |
| `MATCH_LLM_*`, `BRIEF_LLM_*`, `INVENTORY_LLM_*` | fall back to `LLM_*` | give scoring, posting briefs or the skill inventory their own model |
| `VOYAGE_API_KEY` | — | required |
| `VOYAGE_EMBED_MODEL` / `VOYAGE_EMBED_DIMS` / `VOYAGE_RERANK_MODEL` | `voyage-4-lite` / `1024` / `rerank-2.5-lite` | dimension must match the Atlas indexes |
| `NEAR_MISS_THRESHOLD` | `0.35` | calibrated on `voyage-4-lite`; re-measure if the model changes |
| `SCRAPE_*` | | User-Agent, per-host concurrency, page caps, fallback filters |
| `TAILORED_DIR` | | where tailored `.tex` files are written |

**`app/web/.env.local`**

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_AI_URL=http://127.0.0.1:8001/api
```

> Changing `VOYAGE_EMBED_MODEL` or `VOYAGE_EMBED_DIMS` invalidates every stored vector. Re-create
> the Atlas indexes and re-index — it is a migration, not a config tweak. Never put the Voyage key
> in `server/.env` or anything `NEXT_PUBLIC_`-prefixed.

---

## Usage

1. **My Details** — enter your experience, skills, education and certifications. Saving re-cuts
   your profile into retrieval chunks.
2. **Settings** — save your target roles, skills and locations, switch companies on or off, and
   **Run discovery** (optionally "up to N new").
3. **Capture** — on any other career page, open the extension popup and press **Capture**.
4. **Analyze / Refresh** — scores every unscored job; progress appears as toasts.
5. **Job details → Keywords** — review Present, Missing and risk flags; tick the Missing keywords
   you can honestly claim. Nothing is ticked for you.
6. **Preview** — review the tailored `.tex` diff, download `.tex` or PDF.
7. **Apply** — open the application in Chrome, press **Fill this form**, answer anything outlined
   amber, attach the resume, and submit it yourself.
8. **Pipeline / Applications** — track where each application stands.

---

## Project Structure

```
job-search/
├── app/
│   ├── web/src/
│   │   ├── app/            App Router — routes and screens, incl. login/ signup/ jobs/[id]/{keywords,preview}
│   │   ├── component/      app components + ui/ primitives
│   │   ├── layout/         AppShell · Sidebar · Topbar
│   │   ├── services/       one file per API resource; screens import "@/services"
│   │   ├── lib/            the axios instances and ApiError
│   │   ├── hook/ util/ routes/
│   │   └── style/          globals.scss — the only stylesheet
│   └── extension/src/
│       ├── content.ts  background.ts  popup/       thin entrypoints
│       ├── features/       fieldFill · ats (workday, greenhouse, lever, linkedin) · capture
│       │                   · jobContext · answerBank · panel
│       └── shared/
│
├── server/                 REST API — the only process with a database connection
│   ├── main.py             mounts each module's router, CORS, error handler
│   ├── modules/<name>/     __init__ (public interface) · router · service · models
│   │                       account · profile · preference · template · resume · resume_chunk
│   │                       skill_inventory · job · job_description · career_source · match
│   │                       application · event · status · error_log
│   ├── config/             settings, database, auth deps
│   ├── seed_*.py  import_*.py  migrate_*.py  backfill_*.py   one-off scripts
│   └── tests/
│
├── ai/                     the AI tier — no database, no credentials
│   ├── main.py             mounts each api module at /api/{PREFIX}
│   ├── api/                discovery · capture · analysis · scoring · tailoring · settings
│   ├── agents/             parsing · analysis · matching · inventory · tailoring · evidence
│   ├── rag/                embeddings · indexing · retrieval (Voyage)
│   ├── sources/            career-page scraping: http (robots-checked fetcher) · base · run · workday
│   ├── mcp_servers/jobpilot_api/   HTTP client for the server's API (not yet an MCP server)
│   ├── config/             llm (the one LLM client and its roles) · errors · paths · error_log
│   └── tests/
│
├── templates/              six resume designs (Template1…6) with {{TOKEN}} placeholders
├── docs/                   06 data model · 07 PDF setup · 08 career-page registry
└── 01-PRD … 05-Roadmap     planning documents
```

---

## Tests

```bash
cd server && .venv/bin/python -m pytest      # 155 tests, against a throwaway jobpilot_test database
cd ai && .venv/bin/python -m pytest          # 267 tests, model and API faked
cd ai && .venv/bin/python -m pytest -m llm   # 3 adversarial tests against the real local model
cd app/extension && npm run typecheck
```

The server suite needs a running local `mongod`. `ai/tests/test_guardrails.py` scans every tier's
source for the invariants: no hosted LLM endpoint, secrets server-side only, loopback binds, no
form submission anywhere in the extension, and no imports across tiers or module internals.

---

## Documentation

| Doc | Contents |
|---|---|
| [01 — Product Requirements](01-PRD-Product-Requirements-Document.md) | Vision, problem, goals, scope, success metrics |
| [02 — Software Requirements](02-SRS-Software-Requirements-Specification.md) | Functional and non-functional requirements |
| [03 — Architecture & System Design](03-Architecture-System-Design.md) | Component design, data architecture, sequence flows |
| [04 — UI/UX Wireframes & User Flows](04-UIUX-Wireframes-User-Flows.md) | Screens and end-to-end flows |
| [05 — Roadmap](05-Roadmap-Backlog.md) | Twelve phases — every task, its id and its status |
| [06 — Data Model / ER](docs/06-Data-Model-ER.md) | ER diagram, every collection's fields and indexes |
| [07 — PDF Setup (macOS)](docs/07-PDF-Setup-macOS.md) | Installing pdflatex for the `.pdf` download |
| [08 — Career-page scraping](docs/08-Career-Page-Scraping.md) | How postings are pulled from career pages, and the registry of 119 companies by platform |

> **The planning documents (01–04) predate several decisions** and are wrong on them:
> authentication was built (PRD §4 and SRS §42 rule it out); PDF compilation was built (SRS FR-4.4
> says `.tex` only); there is one database rather than a local-plus-Atlas split; agents reach data
> through `server`'s REST API rather than the MongoDB MCP Server (SRS FR-8.1); templating is
> `{{TOKEN}}` substitution, not Jinja2; and Voyage is used for embeddings and reranking, which
> narrows SRS NFR-3 to "all generation is local".

---

## Roadmap

**Make the whole application work end to end first, then make it intelligent.** Every task, its id
and its status live in one place — **[05-Roadmap-Backlog.md](05-Roadmap-Backlog.md)** — and are not
copied here, because a copy is a second roadmap that goes stale.

| Phase | Delivers | State |
|---|---|---|
| 1 | Sign in, and the profile everything hangs off | ✅ |
| 2 | A resume built from that profile, downloadable | 🚧 |
| 3 | Real jobs in the system, searchable and shortlistable | 🚧 |
| 4 | Tracking what you applied to, and the preferences driving it | 🚧 |
| 5 | A resume rectified against a specific job | ✅ |
| 6 | Retrieval over your own resume | ✅ |
| 7 | MCP tool servers | ⬜ |
| 8 | LangGraph agents under a supervisor, with approval interrupts | ⬜ |
| 9 | Form autofill in your own browser session | 🚧 |
| 10 | Ragas faithfulness, guardrail tests, tracing | ⬜ |
| 11 | What only real daily use reveals | ⬜ |
| 12 | Postings pulled straight from company career pages, in eleven stages | 🚧 |

---

## Design Principles

- **No fabrication.** Only keywords you explicitly tick reach the tailored resume, and the server
  refuses anything else. Every model answer that quotes a source is checked against that source
  before it is used; retrieval finds what you already have and is never permission to claim more.
- **No auto-submit.** The extension fills and highlights. It has no code path that submits a form,
  clicks a submit control or dispatches a submit event.
- **A human at every consequential step.** Keyword selection and application review are gates you
  answer, not steps that run past you.
- **Generation is local.** Every LLM call goes to Ollama by default; Voyage embedding and reranking
  are the stated exception — see [What leaves your machine](#what-leaves-your-machine).
- **Localhost only.** `server` and `ai` bind `127.0.0.1`; CORS admits the dashboard and the
  extension.
- **One database, one owner.** Only `server` connects to MongoDB; `ai` holds no URI and works
  through the API with your forwarded token.
- **Real browser session for applying.** The extension works inside your own logged-in session
  rather than an automated browser.
- **Single user, with real accounts.** Built for one person, but with argon2-hashed accounts and JWT
  sessions, and every record keyed to its owner.

## License

Personal project — no license granted for reuse. All rights reserved.
