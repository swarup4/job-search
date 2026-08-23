# JobPilot

**A personal, agentic AI job-search co-pilot — fully local, single-user, no cloud LLM dependency.**

JobPilot discovers relevant job openings, analyzes how well they match your resume, tailors your resume per job description, and helps you fill out applications — all through a set of coordinated AI agents running entirely on your own machine.

> ⚠️ **Personal project.** Built for single-user use. No auth system, no multi-tenant support, and not intended for public deployment as-is.

---

## Table of Contents

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

## Why

Manually job hunting at scale is repetitive: searching multiple sources daily, reading every JD to judge fit, tailoring a resume without over- or under-claiming skills, filling near-identical application forms across ATS platforms, and tracking it all in a spreadsheet. JobPilot automates the repetitive parts while keeping a human decision at every step that matters — what gets added to your resume, and whether an application actually gets submitted.

## Features

- 🔍 **Automated job discovery** — pulls fresh listings daily from Google/SerpAPI, Indeed (via MCP), LinkedIn, and Naukri
- 🎯 **JD keyword matching & gap analysis** — extracts technical keywords from a JD, diffs them against your resume, and shows you exactly what's present vs. missing
- 🧠 **RAG-backed retrieval** — your resume is chunked and embedded into a vector store, so tailoring and scoring work against what your resume actually says rather than a keyword list
- ✅ **Interactive keyword selection** — you choose which missing keywords to incorporate; nothing gets added to your resume without explicit approval
- 📄 **Resume tailoring** — generates a tailored `.tex` (LaTeX) resume per job, built on your own template
- 🧩 **Chrome extension autofill** — fills application forms inside your real, already-logged-in browser session; you always review and submit manually
- 📊 **Pipeline tracking** — status board (Applied → Viewed → Interview → Offer/Rejected) with follow-up reminders, synced to Google Sheets
- 🤖 **Fully local LLM inference** — runs on Ollama/vLLM; no resume or JD data is ever sent to a third-party hosted AI API

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
| Local MongoDB | `jobs`, `matches`, `applications`, `events`, `profile`, `resume_chunk_text` | `server` |
| MongoDB Atlas | `jd_embedding`, `resume_chunks` — **vectors and ids only** | `ai/rag` |

`server/.env` holds the local URI and no Atlas URI; `ai/.env` holds the Atlas URI and no local URI. Neither service can reach the other's store, even by mistake.

**Atlas never receives resume or JD prose.** Vector search returns `chunk_id`s, and the text is fetched from `server` on a second local hop. That costs one HTTP call per retrieval and keeps the privacy guarantee real rather than aspirational.

> **Note on the design docs.** Two decisions here supersede the planning documents: the dashboard is Next.js rather than Streamlit/Gradio, and agents reach structural data through `server`'s REST API rather than the MongoDB MCP Server (SRS FR-8.1). Both are deliberate — the API route gives one validation boundary and keeps DB credentials out of the agent process. Docs 02 and 03 still describe the earlier shape.

## Tech Stack

| Layer | Choice |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Tool protocol | [MCP](https://modelcontextprotocol.io/) (self-hosted servers) |
| LLM serving | [Ollama](https://ollama.com/) (dev) / [vLLM](https://github.com/vllm-project/vllm) (production-like) |
| Models | Qwen2.5-32B+/Llama 3.3-70B (orchestration, tailoring) · Qwen2.5-7B/14B (discovery, scoring) · BGE-M3/nomic-embed-text (embeddings) |
| Database — structural | Local MongoDB (native install) |
| Database — vector / RAG | [MongoDB Atlas](https://www.mongodb.com/atlas) (free M0 tier, `$vectorSearch`) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) (Python, `uv`) |
| Frontend | [Next.js](https://nextjs.org/) (JavaScript, App Router) |
| Browser automation (discovery only) | [Playwright](https://playwright.dev/) |
| Application autofill | Custom Chrome Extension (Manifest V3, TypeScript) |
| Resume templating | [Jinja2](https://jinja.palletsprojects.com/) over a LaTeX template |
| Queue / scheduling | Redis + Celery |
| Eval/observability | [Langfuse](https://langfuse.com/) or [Phoenix](https://phoenix.arize.com/) (self-hosted) |

## Getting Started

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 18+ and npm
- [Ollama](https://ollama.com/download) installed locally, with a chat model and an embedding model pulled:
  ```bash
  ollama pull qwen2.5:32b
  ollama pull nomic-embed-text
  ```
- MongoDB installed locally ([macOS via Homebrew](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/))
- A free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) account (M0 tier) with a `$vectorSearch` index on the vector collections
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
uv run uvicorn server.main:app --reload --host 127.0.0.1 --port 8000

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
MONGODB_LOCAL_URI=mongodb://localhost:27017/jobpilot
REDIS_URL=redis://localhost:6379
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/sheets.json
GOOGLE_SHEET_ID=<your-sheet-id>
```

**`ai/.env`** — vectors and inference, no local DB access:

```bash
MONGODB_ATLAS_URI=<your-atlas-connection-string>
REDIS_URL=redis://localhost:6379

OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:32b
EMBEDDING_MODEL=nomic-embed-text

JOBPILOT_API_BASE_URL=http://localhost:8000
SERPAPI_KEY=<your-key>
INDEED_MCP_URL=<your-indeed-mcp-endpoint>
```

**`app/web/.env.local`**:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> Changing `EMBEDDING_MODEL` invalidates every stored vector. Treat it as a migration and re-index, not a config tweak.

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

```
jobpilot/
├── app/
│   ├── web/                        # Next.js dashboard (JavaScript)
│   │   ├── public/
│   │   └── src/
│   │       ├── app/                #   App Router — thin re-exports only
│   │       ├── page/               #   the real screen components
│   │       ├── component/          #   reusable UI
│   │       ├── layout/             #   app shell, pending-review banner
│   │       ├── routes/             #   path constants
│   │       ├── api/                #   one client module per server module
│   │       ├── hook/
│   │       └── util/
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
│   ├── modules/                    #   job · match · resume · application · event · profile
│   │   └── <name>/
│   │       ├── __init__.py         #     public interface
│   │       ├── router.py
│   │       ├── service.py
│   │       ├── repository.py       #     the only place this module's collections are touched
│   │       ├── models.py
│   │       └── tests/
│   └── config/                     #   settings.py · database.py · deps.py
│
├── ai/                             # agents, RAG, orchestration, MCP
│   ├── agents/                     #   discovery · matching · tailoring · application · tracking
│   ├── rag/                        #   embeddings · chunking · indexing · retrieval
│   │   ├── atlas.py                #     the Atlas client
│   │   └── repository.py           #     the only place Atlas collections are touched
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
| [05 — Roadmap & Backlog](05-Roadmap-Backlog.md) | Phased roadmap, epics, sprint breakdown |

## Roadmap

- [x] Project planning & architecture
- [ ] Phase 0 — Foundation (DB setup, LLM validation, `$vectorSearch` index)
- [ ] Phase 1 — Job Discovery Agent
- [ ] Phase 2 — JD Match & Resume Tailor Agents
- [ ] Phase 3 — Application Agent (Chrome extension)
- [ ] Phase 4 — Tracking Dashboard
- [ ] Phase 5 — Multi-agent Orchestration
- [ ] Phase 6 — Eval & Guardrails
- [ ] Phase 7 — Daily-use polish

Full detail in [`05-Roadmap-Backlog.md`](05-Roadmap-Backlog.md).

## Design Principles

- **Human approval at every consequential step.** Resume content and application submission both require explicit user action — nothing is fabricated or auto-submitted. The orchestrator pauses at two interrupts and cannot be configured past them.
- **No fabrication.** Only keywords you explicitly check reach the tailored resume. Retrieval finds content you already have; it is never permission to claim something new.
- **Local-first.** LLM inference and all raw text stay on your machine. Only embeddings and identifiers live in Atlas.
- **One tier, one database.** `server` owns the structural store, `ai` owns the vector store, and neither holds the other's connection string. The boundary is enforced by configuration, not by discipline.
- **Real browser session for applying.** The Chrome extension fills forms inside your actual logged-in session rather than a separate automated browser — more reliable, and it avoids anti-bot detection.
- **Single-user by design.** No auth, no multi-tenancy — kept intentionally simple for personal use.

## License

Personal project — no license granted for reuse. All rights reserved.
