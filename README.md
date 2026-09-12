# JobPilot

**A personal, agentic AI job-search co-pilot — local-first, single-user, all generation on your own hardware.**

JobPilot discovers relevant job openings, analyzes how well they match your resume, tailors your resume per job description, and helps you fill out applications — all through a set of coordinated AI agents running entirely on your own machine.

> ⚠️ **Personal project.** Built for single-user use, not intended for public deployment as-is.
> It does now have real accounts and authentication — see [Phase 1](#phase-1--authentication--profile).

> 🚧 **The dashboard and the API exist; the agents do not.** Eleven Next.js screens run, and
> `server/` serves 54 REST endpoints across ten modules over local MongoDB. Signing in works end to
> end; every other screen still reads a JSON fixture. `ai/` is still an empty directory, so there
> are no agents, no RAG, and no LLM call anywhere in the system. Everything below describes the
> intended system — see [Current state](#current-state) for what actually runs today.

---

## Table of Contents

- [Current state](#current-state)
- [Why](#why)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Design Principles](#design-principles)
- [License](#license)

---

## Current state

*Updated 2026-09-12.*

| Area | Status |
|---|---|
| Dashboard UI — 11 screens | **built**. Login and signup run against the live API; My Details persists `role` only; the other eight screens render JSON fixtures from `app/web/src/data/` |
| `app/web` → `server` wiring | **started** — one axios instance in `src/lib/`, one service per API module in `src/services/`, `ApiError` as the single failure shape |
| Form validation | **built** — Formik (`useFormik`) with a Yup schema per form in `src/util/schema.js`; the server's own validation still decides |
| `templates/base_resume.tex` | **written**; Jinja2 render verified — but never compiled by a TeX engine, so its LaTeX validity is unconfirmed |
| `server/` — REST API, local MongoDB | **built** — eight modules, thirteen collections, 51 endpoints over 47 paths, Beanie over local MongoDB. **No tests** (removed on request), so no story is Done per Roadmap §10 |
| Authentication | **built and enforced server-side** — argon2 hashes, JWT on signup and login, route guard, bearer token on every call. Every endpoint but signup, login and refresh needs a token, and no URL carries a user id: `verify_token` reads it from the token, so there is no way to ask for another user's data |
| Per-user data | **every collection is keyed by `userId`** — jobs, matches, resumes, applications, the answer bank and events, as well as the five profile collections. Queries filter on the owner, and dedup keys are unique per user rather than globally |
| `ai/` — agents, RAG, MCP, eval | not started (empty directory) |
| `app/extension/` — Chrome MV3 | not started |

### What you can run today

```bash
# REST API — needs a local mongod running. Start this first:
# My Details calls it, and that page errors if the API is down.
cd server && uv venv && uv pip install -e . && .venv/bin/python main.py

# dashboard
cd app/web && npm install && npm run dev
```

Open http://localhost:3000 for the dashboard, http://localhost:8000/docs for the API. You will be
redirected to `/login` — create an account, and signup signs you straight in. Every screen then
navigates and the Resume Preview renders a real tailored `.tex` from a fixture. The
[Getting Started](#getting-started) commands below target the full system and will still fail on the
`ai/` and extension steps.

Screens that exist: pipeline board, job search, shortlist, job details, keyword selection, resume
preview, staged applications, my details, settings, login, signup.

> **Login and signup are real as of 2026-09-11** — argon2-hashed accounts, JWT sessions, and a guard
> on every dashboard route. This contradicts PRD §4 and SRS §42, which specify no auth on single-user
> grounds; **those documents now need amending**, the decision having gone the other way. Tracked as
> reopened as in scope.

---

## Why

Manually job hunting at scale is repetitive: searching multiple sources daily, reading every JD to judge fit, tailoring a resume without over- or under-claiming skills, filling near-identical application forms across ATS platforms, and tracking it all in a spreadsheet. JobPilot automates the repetitive parts while keeping a human decision at every step that matters — what gets added to your resume, and whether an application actually gets submitted.

## Features

The intended capability set. Today only the profile round-trip is real; keyword selection and the
resume preview are UI against fixtures, and no agent exists — see
[Current state](#current-state).

- 🔍 **Automated job discovery** — pulls fresh listings daily from Google/SerpAPI, Indeed (via MCP), LinkedIn, and Naukri
- 🎯 **JD keyword matching & gap analysis** — extracts technical keywords from a JD, diffs them against your resume, and shows you exactly what's present vs. missing
- 🧠 **RAG-backed retrieval with reranking** — your resume is chunked and embedded, retrieved by vector search, then reranked so tailoring and scoring work against what your resume actually says
- 📐 **Measured, not assumed** — a [Ragas](https://docs.ragas.io/) suite scores retrieval quality and, critically, **faithfulness**: the automated check that nothing was fabricated
- ✅ **Interactive keyword selection** — you choose which missing keywords to incorporate; nothing gets added to your resume without explicit approval
- 📄 **Resume tailoring** — generates a tailored `.tex` (LaTeX) resume per job, built on your own template
- 🧩 **Chrome extension autofill** — fills application forms inside your real, already-logged-in browser session; you always review and submit manually
- 📊 **Pipeline tracking** — status board (Applied → Viewed → Interview → Offer/Rejected) with follow-up reminders, synced to Google Sheets
- 🤖 **All generation runs locally** — every LLM call that writes, decides, or scores runs on Ollama/vLLM. Embedding and reranking use Voyage's hosted API; see [what leaves your machine](#what-leaves-your-machine)

## Architecture

Three independent services and two databases:

```
   app/web (:3000)          app/extension
          │                       │
          └────── HTTP ───────────┴──▶  server (:8000)  ──▶  Local MongoDB
                                            ▲        │            (structural data)
                                      HTTP  │        │ Redis
                                            │        ▼
                                        ai (worker)  ──▶  MongoDB Atlas
                                                             (RAG / vectors)
```

| Service | Responsibility | Owns |
|---|---|---|
| **`app/web`** | Next.js dashboard — shortlist review, keyword selection, pipeline board | nothing (pure client) |
| **`server`** | REST APIs, all structural data access | **Local MongoDB** |
| **`ai`** | LangGraph agents, RAG pipeline, MCP tool servers | **MongoDB Atlas** (vectors) |

The five agents run as LangGraph nodes inside the `ai` worker, under a supervisor that pauses at two human-approval interrupts:

```
                        ┌─────────────────────────┐
                        │   Orchestrator Agent      │
                        │   (LangGraph Supervisor)  │
                        └────────────┬──────────────┘
             ┌───────────────┬───────┴───────┬────────────────┬───────────────┐
             ▼               ▼               ▼                ▼               ▼
   ┌─────────────────┐ ┌───────────┐ ┌───────────────┐ ┌──────────────┐ ┌─────────────┐
   │ Job Discovery    │ │ JD Match/ │ │ Resume Tailor  │ │ Application  │ │ Tracking &  │
   │ Agent            │ │ Score     │ │ Agent          │ │ Agent        │ │ Follow-up   │
   │                  │ │ Agent     │ │                │ │ (Chrome ext) │ │ Agent       │
   └─────────────────┘ └───────────┘ └───────────────┘ └──────────────┘ └─────────────┘
```

### How the tiers communicate

- **`ai` → `server`**: HTTP, through the `jobpilot_api` MCP server. This is how agents read and write jobs, matches, applications, events, and profile data.
- **`server` → `ai`**: Redis. `server` enqueues agent runs; the `ai` worker's Celery consumers pick them up.
- **Never by import.** The two tiers share no Python code, which keeps them independently deployable.

### Two databases, one connection string each

| Store | Holds | Owner |
|---|---|---|
| Local MongoDB | `accounts`, `profile`, `work_experience`, `education`, `skills`, `certifications`, `jobs`, `matches`, `resumes`, `applications`, `answer_bank`, `events`, `templates` | `server` |
| MongoDB Atlas | `jd_embedding`, `resume_chunks` — **vectors and ids only** | `ai/rag` |

`server/.env` holds the local URI and no Atlas URI; `ai/.env` holds the Atlas URI and no local URI. Neither service can reach the other's store, even by mistake.

**Atlas never receives resume or JD prose.** Vector search returns `chunk_id`s, and the text is fetched from `server` on a second local hop.

### What leaves your machine

Being precise about this matters more than a reassuring one-liner:

| | Stays local | Goes to Voyage |
|---|---|---|
| Every LLM call that writes, decides, extracts, or scores | ✅ | |
| Prompts, tailored resumes, cover letters, keyword decisions | ✅ | |
| Chunk text and JD text, when embedded | | ⚠️ |
| Query + candidate chunks, when reranked | | ⚠️ |
| Ragas judging (contexts + generated output) | ✅ local judge | |

So resume and JD prose **does** reach Voyage's API in flight. What never leaves is generation: no prompt and no generated content touches a hosted provider, and no other cloud AI service is used at all.

Two-stage retrieval: Voyage embed → `$vectorSearch` (top ~50) → fetch text from `server` → Voyage rerank → top ~5.

> **Notes on the design docs.** Five decisions supersede the planning documents. (1) The dashboard is Next.js, not Streamlit/Gradio. (2) Agents reach structural data through `server`'s REST API rather than the MongoDB MCP Server (SRS FR-8.1) — one validation boundary, and no DB credentials in the agent process. (3) **SRS NFR-3 forbids sending any data to third-party inference APIs; using Voyage narrows that to "all generation is local."** If the original absolute guarantee matters more than retrieval quality, swap `ai/rag/embeddings.py` and `reranking.py` for a local embedding model — the rest of the pipeline is unchanged. (4) **Authentication was built**, which PRD §4 and SRS §42 rule out; accounts are argon2-hashed and sessions are JWTs, so those two documents are now wrong and need amending. (5) **`profile.preferences` and `resume_chunk_text` were removed** on 2026-09-11, and the profile became five collections keyed by `userId`; docs 02, 03 and 06 still describe the earlier single-document shape with a RAG chunk store.

## Tech Stack

| Layer | Choice |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Tool protocol | [MCP](https://modelcontextprotocol.io/) (self-hosted servers) |
| LLM serving | [Ollama](https://ollama.com/) (dev) / [vLLM](https://github.com/vllm-project/vllm) (production-like) |
| Generation models | Qwen2.5-32B+/Llama 3.3-70B (orchestration, tailoring) · Qwen2.5-7B/14B (discovery, scoring) — all local |
| Embeddings + reranking | [Voyage AI](https://www.voyageai.com/) (hosted; MongoDB-owned, pairs natively with Atlas) |
| Database — structural | Local MongoDB (native install) |
| Database — vector / RAG | [MongoDB Atlas](https://www.mongodb.com/atlas) (free M0 tier, `$vectorSearch`) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) (Python, `uv`) |
| Frontend | [Next.js](https://nextjs.org/) (JavaScript, App Router) |
| UI | [Tailwind CSS](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/) (components copied in, not a dependency) |
| HTTP client | [axios](https://axios-http.com/) — one instance in `app/web/src/lib/`, with `ApiError` as the single failure shape |
| Form state + validation | [Formik](https://formik.org/) (`useFormik`) + [Yup](https://github.com/jquense/yup) — one schema per form in `app/web/src/util/schema.js` |
| Browser automation (discovery only) | [Playwright](https://playwright.dev/) |
| Application autofill | Custom Chrome Extension (Manifest V3, TypeScript) |
| Resume templating | [Jinja2](https://jinja.palletsprojects.com/) over a LaTeX template |
| Queue / scheduling | Redis + Celery |
| RAG evaluation | [Ragas](https://docs.ragas.io/) — faithfulness, context precision/recall, with a **local** judge |
| Observability | [Langfuse](https://langfuse.com/) or [Phoenix](https://phoenix.arize.com/) (self-hosted) |

## Getting Started

> **These instructions describe the finished system and do not all work yet.** Missing today:
> no root `pyproject.toml` (so `uv sync` fails), no root `package.json` (so a root `npm install`
> fails), no `ai/.env.example` to copy, no `ai/orchestration/worker.py`, and no `app/extension/`.
> `server/` and `app/web/` both run today — see
> [What you can run today](#what-you-can-run-today) for the commands that work.

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 18+ and npm
- [Ollama](https://ollama.com/download) installed locally, with a chat model pulled:
  ```bash
  ollama pull qwen2.5:32b
  ```
  No local embedding model is needed — embeddings come from Voyage.
- A [Voyage AI](https://www.voyageai.com/) API key, for embeddings and reranking (paid per token)
- MongoDB installed locally ([macOS via Homebrew](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/))
- A free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) account (M0 tier) with a `$vectorSearch` index whose **dimension matches your chosen Voyage embedding model**
- Redis (`brew install redis` on macOS)
- Google Chrome, for loading the extension in developer mode

### Installation

```bash
git clone https://github.com/<your-username>/jobpilot.git
cd jobpilot

# Python dependencies for both backend services
uv sync

# Frontend dependencies
npm install

# Each service gets its own env file — see Configuration below
cp server/.env.example server/.env
cp ai/.env.example ai/.env
cp app/web/.env.example app/web/.env.local

# Backing services
brew services start mongodb-community
brew services start redis
```

### Running

Three services, each startable independently:

```bash
# 1. REST API + local MongoDB
#    Run from server/ — main.py imports `config`, not `server.config`
cd server && uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 2. AI worker — agents, RAG, scheduled discovery
uv run celery -A ai.orchestration.worker worker --beat

# 3. Dashboard
cd app/web && npm run dev
```

Then open http://localhost:3000.

The dashboard works with `server` alone; the `ai` worker is what makes discovery, scoring, and tailoring happen.

### Loading the Chrome Extension

1. Build it: `cd app/extension && npm install && npm run build`
2. Open `chrome://extensions`
3. Enable **Developer mode** (top right)
4. Click **Load unpacked** and select `app/extension/dist`

## Configuration

Each service reads its own `.env`. The split is deliberate — it makes it impossible for one tier to reach the other's database.

**`server/.env`** — structural data, no Atlas access:

```bash
MONGODB_LOCAL_URI=mongodb://127.0.0.1:27017
MONGODB_DB_NAME=jobpilot
HOST=127.0.0.1
PORT=8000
WEB_ORIGIN=http://localhost:3000
```

Those five are everything `server` reads today, and each has a default in code — an absent `.env`
still boots against a local mongod. `.env` is loaded once, in `server/config/__init__.py`, anchored
to `server/.env` rather than the process's working directory. `REDIS_URL` and the Google Sheets
credentials arrive with Phases 3 and 6; there is no settings class, so a variable nothing reads is
simply ignored.

**`ai/.env`** — vectors and inference, no local DB access:

```bash
MONGODB_ATLAS_URI=<your-atlas-connection-string>
REDIS_URL=redis://localhost:6379

# Generation — always local
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:32b

# Embeddings + reranking — Voyage (hosted). Verify model names against Voyage's docs.
VOYAGE_API_KEY=<your-key>
VOYAGE_EMBED_MODEL=<embedding-model>
VOYAGE_EMBED_DIM=<must match the Atlas $vectorSearch index>
VOYAGE_RERANK_MODEL=<rerank-model>

JOBPILOT_API_BASE_URL=http://localhost:8000
SERPAPI_KEY=<your-key>
INDEED_MCP_URL=<your-indeed-mcp-endpoint>
```

**`app/web/.env.local`**:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

The `/api` suffix is part of the value — `src/lib/axiosInstance.js` uses it as the axios `baseURL`
verbatim and appends no prefix of its own.

> The Voyage key belongs to `ai/.env` alone — never `server/.env`, and never anything `NEXT_PUBLIC_` prefixed, which would ship it to every browser.
>
> Changing `VOYAGE_EMBED_MODEL` or `VOYAGE_EMBED_DIM` invalidates every stored vector and requires re-creating the Atlas index. Treat it as a migration and re-index, not a config tweak.

## Usage

1. **Set your profile** — add your target roles, locations, and resume data in the dashboard's Profile section. This is also what gets chunked and embedded for retrieval.
2. **Let discovery run** — the scheduled job pulls new listings daily; check the Dashboard for the "New" column
3. **Review a match** — click a job card to see the JD match score and Present/Missing keyword lists
4. **Select keywords** — check which missing keywords to incorporate, then tailor the resume
5. **Review the `.tex`** — check the tailored resume diff before staging
6. **Apply** — open the application page in Chrome, let the extension autofill known fields, review, attach your resume, and submit manually
7. **Track** — monitor pipeline status and follow-up reminders from the Dashboard

## Project Structure

Organized by **capability**, not by technical layer. Each module is a vertical slice.

**This is the target layout.** Today `app/web/`, `server/` and `templates/` exist; `ai/` and
`app/extension/` are empty or absent. See [Current state](#current-state).

```
jobpilot/
├── app/
│   ├── web/                        # Next.js dashboard (JavaScript)
│   │   ├── public/
│   │   └── src/
│   │       ├── app/                #   App Router — routes AND screens
│   │       │                       #   incl. login/ signup/ and jobs/[id]/{keywords,preview}
│   │       ├── component/          #   app components + ui/ primitives
│   │       ├── layout/             #   AppShell · Sidebar · Topbar
│   │       ├── routes/             #   path constants + sidebar IA
│   │       ├── lib/                #   axiosInstance.js — the one client + ApiError
│   │       ├── services/           #   one file per API module; screens import "@/services"
│   │       ├── data/               #   JSON fixtures, for screens not yet on services/
│   │       ├── hook/  util/        #   util/schema.js — Yup schemas + their initialValues
│   │       └── style/              #   globals.scss (SCSS throughout)
│   └── extension/                  # Chrome extension (MV3, TypeScript)
│       └── src/
│           ├── content.ts          #   thin entrypoints
│           ├── background.ts
│           ├── popup/
│           ├── features/           #   fieldFill · ats · jobContext · answerBank
│           └── shared/
│
├── server/                         # REST APIs + local MongoDB
│   ├── main.py                     #   mounts module routers, nothing else
│   ├── errors.py                   #   NotFound/Conflict/Invalid → HTTP, in one handler
│   ├── modules/                    #   job · match · resume · application · event · profile
│   │   └── <name>/
│   │       ├── __init__.py         #     public interface
│   │       ├── router.py
│   │       ├── service.py          #     domain logic and this module's queries
│   │       └── models.py
│   └── config/                     #   __init__.py (loads .env) · database.py
│
├── ai/                             # agents, RAG, orchestration, MCP
│   ├── agents/                     #   discovery · matching · tailoring · application · tracking
│   ├── rag/                        #   chunking · indexing · two-stage retrieval
│   │   ├── embeddings.py           #     Voyage embeddings — one of two files that may call Voyage
│   │   ├── reranking.py            #     Voyage reranker — the other
│   │   ├── atlas.py                #     the Atlas client
│   │   └── repository.py           #     the only place Atlas collections are touched
│   ├── eval/                       #   Ragas: datasets · metrics · judge (local) · run
│   ├── orchestration/              #   graph.py · state.py · interrupts.py
│   ├── mcp_servers/                #   jobpilot_api · job_search · indeed · linkedin · latex · browser
│   └── config/                     #   settings.py · llm.py · mcp.py
│
├── templates/
│   └── base_resume.tex             # Jinja2 with \VAR{} / \BLOCK{} delimiters
└── 01-PRD…05-Roadmap.md            # planning documents (see below)
```

Server modules are named after the **resource** they expose; agents after the **capability** they perform.

## Documentation

| Doc | Contents |
|---|---|
| [01 — Product Requirements Document](01-PRD-Product-Requirements-Document.md) | Vision, problem, goals, scope, success metrics |
| [02 — Software Requirements Specification](02-SRS-Software-Requirements-Specification.md) | Functional & non-functional requirements |
| [03 — Architecture & System Design](03-Architecture-System-Design.md) | Component design, data architecture, deployment |
| [04 — UI/UX Wireframes & User Flows](04-UIUX-Wireframes-User-Flows.md) | Screens and end-to-end flows |
| [05 — Roadmap](05-Roadmap-Backlog.md) | Eleven phases, application first then agents — every task checkboxed and split API vs UI |
| [06 — Data Model / ER](docs/06-Data-Model-ER.md) | ER diagram, every collection's fields and indexes, and where each guardrail is enforced in the schema |

## Roadmap

**Make the whole application work end to end first, then make it intelligent.** Phases 1–4 build a
product usable by hand. Phase 5 adds the first LLM. Phases 6–11 turn that into the agentic system.
An agent writing into a half-built app cannot be judged — so the plumbing is finished first.

Each phase is split by **API** and **UI**, because they rarely land together here: most screens were
built before the backend and are still waiting to be wired to endpoints that already exist. A checked
UI box means the screen is built, **not** that it talks to the API — that wiring is its own task.

#### Phase 1 — Authentication & Profile 🚧 API done, one UI wiring task left

- **API**
  - ✅ `accounts` with argon2 hashes; signup and login both issue a JWT
  - ✅ `account` module — signup (name, email, password and nothing else), login,
    refresh, read, partial update
  - ✅ Profile as five collections keyed by `userId`
  - ✅ Server-side token enforcement; `userId` comes from the token, never the URL
  - ✅ Access token refreshed by a longer-lived refresh token, so the 60-minute TTL
    does not mean signing in every hour
  - ✅ Retired the duplicate `user` module, which held plaintext passwords
- **UI**
  - ✅ Login, signup and sign-out, wired to `/api/account`
  - ✅ Route guard, session in `sessionStorage` mirrored into Redux
  - ✅ A 401 refreshes once and replays the call before dropping the session
  - ✅ My Details screen, with Formik/Yup validation
  - ⬜ Wire My Details to the profile API, only `role` persists today

#### Phase 2 — Resume generation & download 🚧 backend done, no UI

- **API**
  - ✅ `templates` collection, upload with token validation, style inference
  - ✅ Render the signed-in user's profile into a template
  - ⬜ `.tex` download
  - ⬜ PDF compilation
- **UI**
  - ✅ Resume Preview screen — Preview / Diff / Source tabs
  - ⬜ Wire it to a real render instead of `resume.json`
  - ⬜ Template picker
- ⬜ **Prove a rendered `.tex` compiles under a TeX engine** — none ever has

#### Phase 3 — Job scraping, search & shortlist ⬜ API only

- **API**
  - ✅ `job` module — dedup-hash create, list by status, shortlist
  - ⬜ Indeed and SerpAPI sources
  - ⬜ Content-hash dedup
  - ⬜ Scheduled daily run *(needs Redis + Celery)*
- **UI**
  - ✅ Job Search, Shortlist and Job Details screens
  - ⬜ Wire all three off `search.json` and onto the job API

#### Phase 4 — Applications & Settings ⬜ API only

- **API**
  - ✅ `application` module — stage, record fill, status transitions, answer bank
  - ⬜ Rebuild a preferences store for Settings
  - ⬜ Follow-up drafts and Google Sheet sync
- **UI**
  - ✅ Pipeline board, Staged Applications, Settings screens
  - ⬜ Wire them to the application API and real counts

#### Phase 5 — LLM integration & resume rectification ⬜ not started

- **API**
  - ✅ `match` and `resume` modules
  - ⬜ JD keyword extraction and Present/Missing diff
  - ⬜ Tailor using **only** the keywords you ticked
  - ⬜ Match scoring by embedding *(needs Atlas)*
- **UI**
  - ✅ Keyword Selection screen, starting with nothing checked
  - ⬜ Wire it to real match data
- ⬜ Validate a local LLM's tool-calling

#### Phase 6 — RAG & retrieval ⬜ not started

- **API**
  - ⬜ Rebuild the RAG second hop — `resume_chunk_text` and text fetch by `chunk_id`
  - ⬜ Chunk the profile into retrievable units
  - ⬜ Re-index on profile edit
- **AI tier**
  - ⬜ Embed chunks into Atlas — ids and vectors only, never prose
  - ⬜ Two-stage retrieval: `$vectorSearch` → fetch text → rerank
  - ⬜ Atlas free tier + `$vectorSearch` index

#### Phase 7 — MCP tool servers ⬜ not started

- ⬜ `jobpilot_api` — the one way agents touch structural data
- ⬜ `latex` — render a tailored `.tex`
- ⬜ `job_search`, `indeed`, `linkedin`, `browser`

#### Phase 8 — Agents & orchestration ⬜ not started

- **AI tier**
  - ⬜ Discovery, Match/Score, Tailor and Tracking agents
  - ⬜ LangGraph supervisor with shared state
  - ⬜ **Human-approval interrupts** at keyword selection and application review
  - ⬜ Retry and error handling per step
- **UI**
  - ⬜ Surface an interrupt in the dashboard — the approval gate needs somewhere to happen

#### Phase 9 — Application agent & Chrome extension ⬜ not started

- **Extension**
  - ⬜ MV3 scaffold, field detection, LLM fallback
  - ⬜ Highlight filled fields, manual resume attach
  - ⬜ Workday / Greenhouse / Lever, then LinkedIn Easy Apply
- **API**
  - ⬜ Serve job context and the Q&A answer bank
  - ⬜ Application agent coordinating the fill

#### Phase 10 — Eval, guardrails & observability ⬜ not started

- ⬜ Ragas suite — **faithfulness** is the automated no-fabrication check
- ⬜ Eval datasets from real JDs and profile content, with a **local** judge
- ⬜ No-fabrication and no-auto-submit test cases
- ⬜ Langfuse or Phoenix, self-hosted

#### Phase 11 — Daily use & polish ⬜ not started

- ⬜ Bug fixes from actually running the workflow daily
- ⬜ Q&A answer-bank refinement, local-model cost tuning
- ⬜ Cover letter generation *(stretch)*

### True of every phase

- ⬜ **No tests**, removed on request, so no story meets the Definition of Done
- ⬜ **`userId` comes from the URL, not the token**; any signed-in account can reach
  another's profile

Full detail, every task and its status: [`05-Roadmap-Backlog.md`](05-Roadmap-Backlog.md).

## Design Principles

- **Human approval at every consequential step.** Resume content and application submission both require explicit user action — nothing is fabricated or auto-submitted. The orchestrator pauses at two interrupts and cannot be configured past them.
- **No fabrication.** Only keywords you explicitly check reach the tailored resume. Retrieval finds content you already have; it is never permission to claim something new.
- **Local-first, stated precisely.** All generation runs on your hardware. Embedding and reranking use Voyage; nothing else leaves. See [What leaves your machine](#what-leaves-your-machine) rather than trusting a slogan.
- **Measured, not assumed.** Ragas faithfulness is the automated proof that the no-fabrication rule holds. A guardrail without a test is a hope — and `server/` currently has none, which is why its guardrail stories are not marked Done.
- **One tier, one database.** `server` owns the structural store, `ai` owns the vector store, and neither holds the other's connection string. The boundary is enforced by configuration, not by discipline.
- **Real browser session for applying.** The Chrome extension fills forms inside your actual logged-in session rather than a separate automated browser — more reliable, and it avoids anti-bot detection.
- **Single-user by design.** No multi-tenancy — kept intentionally simple for personal use.
  *(Amended 2026-09-11: authentication **was** built. Accounts are argon2-hashed with JWT sessions,
  and every profile row is keyed by `accounts._id`. The "no auth" half of this principle no longer
  holds, and PRD §4 / SRS §42 need updating to match.)*

## License

Personal project — no license granted for reuse. All rights reserved.
