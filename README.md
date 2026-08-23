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
- ✅ **Interactive keyword selection** — you choose which missing keywords to incorporate; nothing gets added to your resume without explicit approval
- 📄 **Resume tailoring** — generates a tailored `.tex` (LaTeX) resume per job, built on your own template
- 🧩 **Chrome extension autofill** — fills application forms inside your real, already-logged-in browser session; you always review and submit manually
- 📊 **Pipeline tracking** — status board (Applied → Viewed → Interview → Offer/Rejected) with follow-up reminders, synced to Google Sheets
- 🤖 **Fully local LLM inference** — runs on Ollama/vLLM; no resume or JD data is ever sent to a third-party hosted AI API

## Architecture

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

Agents run as LangGraph nodes in a single local process. Tool access (search, database, browser, LaTeX rendering) goes through MCP servers, keeping tools decoupled from the orchestration framework. Full detail in [`docs/03-Architecture-System-Design.md`](docs/03-Architecture-System-Design.md).

## Tech Stack

| Layer | Choice |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| Tool protocol | [MCP](https://modelcontextprotocol.io/) (self-hosted servers + MongoDB MCP Server) |
| LLM serving | [Ollama](https://ollama.com/) (dev) / [vLLM](https://github.com/vllm-project/vllm) (production-like) |
| Models | Qwen2.5-32B+/Llama 3.3-70B (orchestration, tailoring) · Qwen2.5-7B/14B (discovery, scoring) · BGE-M3/nomic-embed-text (embeddings) |
| Database — structural | Local MongoDB (native install) |
| Database — vector search | [MongoDB Atlas](https://www.mongodb.com/atlas) (free M0 tier, `$vectorSearch`) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| Frontend | Streamlit/Gradio (MVP) |
| Browser automation (discovery only) | [Playwright](https://playwright.dev/) |
| Application autofill | Custom Chrome Extension (Manifest V3) |
| Resume templating | [Jinja2](https://jinja.palletsprojects.com/) over a LaTeX template |
| Cache/queue | Redis + Celery |
| Eval/observability | [Langfuse](https://langfuse.com/) or [Phoenix](https://phoenix.arize.com/) (self-hosted) |

## Getting Started

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/download) installed locally, with a model pulled (e.g. `ollama pull qwen2.5:32b`)
- MongoDB installed locally ([macOS via Homebrew](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/))
- A free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) account (M0 tier) for vector search
- Redis (`brew install redis` on macOS)
- Node.js 18+ (for the Chrome extension build)
- Google Chrome, for loading the extension in developer mode

### Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/jobpilot.git
cd jobpilot

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and fill in environment config
cp .env.example .env

# Start local services
brew services start mongodb-community
brew services start redis

# Run the backend
uvicorn app.main:app --reload

# Run the dashboard
streamlit run dashboard/app.py
```

### Loading the Chrome Extension

1. Build the extension: `cd extension && npm install && npm run build`
2. Open `chrome://extensions` in Chrome
3. Enable **Developer mode** (top right)
4. Click **Load unpacked** and select the `extension/dist` folder

## Configuration

Set the following in your `.env` file:

```bash
# Local LLM
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:32b
EMBEDDING_MODEL=nomic-embed-text

# MongoDB
MONGODB_LOCAL_URI=mongodb://localhost:27017/jobpilot
MONGODB_ATLAS_URI=<your-atlas-connection-string>

# Redis
REDIS_URL=redis://localhost:6379

# Job search sources
SERPAPI_KEY=<your-key>
INDEED_MCP_URL=<your-indeed-mcp-endpoint>

# Google Sheets sync
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/sheets.json
GOOGLE_SHEET_ID=<your-sheet-id>
```

## Usage

1. **Set your profile** — add your target roles, locations, and resume data in the dashboard's Profile section
2. **Let discovery run** — the scheduled job pulls new listings daily; check the Dashboard for the "New" column
3. **Review a match** — click a job card to see the JD match score and Present/Missing keyword lists
4. **Select keywords** — check which missing keywords to incorporate, then tailor the resume
5. **Review the `.tex`** — check the tailored resume diff before staging
6. **Apply** — open the application page in Chrome, let the extension autofill known fields, review, attach your resume, and submit manually
7. **Track** — monitor pipeline status and follow-up reminders from the Dashboard

## Project Structure

```
jobpilot/
├── agents/                # LangGraph agent definitions
│   ├── discovery.py
│   ├── match_score.py
│   ├── resume_tailor.py
│   ├── tracking.py
│   └── orchestrator.py
├── app/                    # FastAPI backend
├── dashboard/               # Streamlit/Gradio dashboard
├── extension/                # Chrome extension (Manifest V3)
├── templates/                  # LaTeX resume templates (Jinja2)
├── mcp_servers/                  # Self-hosted MCP tool servers
├── docs/                           # Full project documentation (see below)
├── .env.example
├── requirements.txt
└── README.md
```

## Documentation

Full planning and design documents live in [`/docs`](docs):

| Doc | Contents |
|---|---|
| [01 — Product Requirements Document](docs/01-PRD-Product-Requirements-Document.md) | Vision, problem, goals, scope, success metrics |
| [02 — Software Requirements Specification](docs/02-SRS-Software-Requirements-Specification.md) | Functional & non-functional requirements |
| [03 — Architecture & System Design](docs/03-Architecture-System-Design.md) | Component design, data architecture, deployment |
| [04 — UI/UX Wireframes & User Flows](docs/04-UIUX-Wireframes-User-Flows.md) | Screens and end-to-end flows |
| [05 — Roadmap & Backlog](docs/05-Roadmap-Backlog.md) | Phased roadmap, epics, sprint breakdown |

## Roadmap

- [x] Project planning & architecture
- [ ] Phase 0 — Foundation (DB setup, LLM validation)
- [ ] Phase 1 — Job Discovery Agent
- [ ] Phase 2 — JD Match & Resume Tailor Agents
- [ ] Phase 3 — Application Agent (Chrome extension)
- [ ] Phase 4 — Tracking Dashboard
- [ ] Phase 5 — Multi-agent Orchestration
- [ ] Phase 6 — Eval & Guardrails
- [ ] Phase 7 — Daily-use polish

Full detail in [`docs/05-Roadmap-Backlog.md`](docs/05-Roadmap-Backlog.md).

## Design Principles

- **Human approval at every consequential step.** Resume content and application submission both require explicit user action — nothing is fabricated or auto-submitted.
- **Local-first.** LLM inference and the bulk of personal data stay on your machine; only vector embeddings live in MongoDB Atlas.
- **Real browser session for applying.** The Chrome extension fills forms inside your actual logged-in session rather than a separate automated browser, which is both more reliable and avoids anti-bot detection issues.
- **Single-user by design.** No auth, no multi-tenancy — kept intentionally simple for personal use.

## License

Personal project — no license granted for reuse. All rights reserved.
