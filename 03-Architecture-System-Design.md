# Architecture & System Design Document

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | Draft v1.0 |

---

## 1. Architecture Overview

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
          │                   │              │                  │               │
          ▼                   ▼              ▼                  ▼               ▼
   Local MongoDB      Atlas ($vectorSearch) Local filesystem  Local MongoDB   Local MongoDB
   (job metadata)     + Local MongoDB       (.tex files)      (applications)  (events, sheet sync)
                       (match/gap data)
```

All agents run as LangGraph nodes in a single Python process (no A2A needed at single-user scale — see Section 4). Tool access (search, DB, browser, LaTeX rendering) goes through MCP servers rather than hard-coded clients, so tools stay swappable independent of the orchestration framework.

---

## 2. Component Design

### 2.1 Orchestrator (LangGraph Supervisor)
- **Responsibility:** Route between agents, hold shared conversation/task state, pause at human-approval interrupts, retry failed steps.
- **State held:** current job queue, in-flight match/tailor/application records, user's pending approvals.
- **Interrupts:** (a) after keyword extraction — waits for user's Missing-keyword selection; (b) after application autofill — waits for user's manual submit action.

### 2.2 Job Discovery Agent
- **Input:** target role/location profile (from `profile` collection)
- **Tools (via MCP):** Google Custom Search/SerpAPI, Indeed MCP connector, LinkedIn scraper (adapted from existing `linkedin-hiring-scraper` skill), Playwright for career-page scraping where no API exists
- **Output:** normalized job records written to local MongoDB `jobs` collection
- **Guardrail:** respects `robots.txt`/rate limits; dedup via content hash before insert

### 2.3 JD Match/Score Agent
- **Input:** JD text (from `jobs`), resume/profile data
- **Process:**
  1. Generate JD embedding → write to Atlas `jobs.jd_embedding`
  2. Run `$vectorSearch` similarity against `profile.resume_chunks` (Atlas)
  3. LLM structured extraction of JD keywords → diff against resume skill list → Present/Missing lists
  4. Write match score + gap lists to local MongoDB `matches`
- **Output:** Present/Missing keyword lists surfaced to the user via dashboard (interrupt point)

### 2.4 Resume Tailor Agent
- **Input:** user's keyword selections (from the interrupt above)
- **Process:** Jinja2 renders `base_resume.tex` template (custom delimiters `\VAR{}`/`\BLOCK{}` to avoid LaTeX brace clashes) using selected keywords + existing resume data + custom commands (`\certrow`, `\jobtitle`, etc.)
- **Output:** `.tex` file written to local filesystem, versioned by job ID, path recorded in local MongoDB `applications`
- **Guardrail:** template only receives explicitly selected keywords — no LLM free-form insertion into the document body

### 2.5 Application Agent (Chrome Extension + Local Backend)
- **Components:**
  - Content script (runs on ATS page, detects/fills fields)
  - Background service worker (calls local FastAPI backend)
  - Popup UI (shows what will be filled, highlights filled fields)
  - Local FastAPI backend (serves job context, Q&A answer bank, resolves ambiguous fields via local LLM call)
- **Flow:** user opens application page → popup shows current job context → extension fills matched fields → user reviews highlighted fields → user manually attaches `.tex`/resume file → user clicks Submit themselves
- **Guardrail:** no programmatic submit; file inputs require manual attach (browser security restriction, applies to any automation approach)

### 2.6 Tracking & Follow-up Agent
- **Input:** application status changes (from extension confirmation, or manual dashboard update)
- **Process:** maintains pipeline state in `applications`/`events`, generates follow-up drafts at configured intervals, pushes status sync to Google Sheets
- **Output:** dashboard status board, reminder surfaced in UI

---

## 3. Data Architecture

### 3.1 Split Store Rationale
Vector search requires either Atlas or a Docker-based local `mongot` (native macOS build doesn't exist). Given macOS as the primary dev environment, vector-search-relevant data goes to **Atlas free tier**; everything else stays on **local MongoDB**, keeping the bulk of personal data off any cloud service.

### 3.2 Local MongoDB (structural)

*As implemented in `server/modules/`. Every `_id` is an `ObjectId`; foreign keys are plain indexed
`ObjectId` fields. Full field lists, indexes and rationale: [doc 06](docs/06-Data-Model-ER.md).*
```
profile            { email UK, personal, summary, experience[], education[], skill_groups[],
                     certifications[], preferences, resume_template_path, chunk_count }
resume_chunk_text  { chunk_id UK, section, text, source_ref }
jobs               { title, company{}, location, job_type, work_mode, experience_band, salary_text,
                     jd_text, summary, responsibilities[], requirements[], source, source_url,
                     posted_at, deadline_at, dedup_hash UK, status, shortlisted }
matches            { job_id UK, score, present[], missing[], risks[], review{state,
                     selected_keys[], reviewed_at}, model_name }
resumes            { job_id + version UK, match_id, file_path, template_path, selected_keys[],
                     incorporated[], declined[], changes[] }
applications       { job_id, resume_id, tex_path, ats, apply_url, status, fields_filled[],
                     screening_answers[], approved_by_user, staged_at, submitted_at,
                     follow_up_due_at }
answer_bank        { key UK, question, answer, tags[], used_count }
events             { job_id, application_id, event_type, actor, notes, payload, occurred_at }
```

Three differences from the original sketch, each deliberate:

- **`resumes` is its own collection.** The sketch put `tex_version`/`tex_path` on `applications`. A
  job can be re-tailored, so the `.tex` needs its own versioned record with the selection set that
  produced it — that record is what makes NFR-8 auditable.
- **No `cover_letter`.** Out of v1 scope (PRD §5).
- **`answer_bank` added.** FR-5.2 needs reusable screening answers; they are not per-application.

### 3.3 MongoDB Atlas (vector-search)
```
jobs.jd_embedding          { job_id, embedding_vector, indexed via $vectorSearch }
profile.resume_chunks      { chunk_id, section, embedding_vector, indexed via $vectorSearch }
```

`job_id` and `chunk_id` are the join keys across the two stores.

**Atlas holds vectors and identifiers only — never resume or JD prose.** The chunk `text` stays in
local `resume_chunk_text`, and retrieval fetches it from `server` between the vector search and the
rerank. Text at rest in a cloud database is a more durable exposure than text in an inference
request.

### 3.4 Data Flow for a Single Job (end to end)
1. Job Discovery Agent writes raw job → local `jobs`
2. JD Match Agent embeds JD → Atlas `jobs.jd_embedding`; runs similarity vs. Atlas `profile.resume_chunks`
3. JD Match Agent writes score + gap lists → local `matches`
4. User selects keywords via dashboard (interrupt)
5. Resume Tailor Agent renders `.tex` → local filesystem; path recorded in local `applications`
6. Chrome extension reads `applications` (via local backend) when user opens the ATS page
7. User submits manually; extension/dashboard updates `applications.status`
8. Tracking Agent writes to `events`, syncs Google Sheet

---

## 4. Integration Architecture

### 4.1 Agent Framework: LangGraph
Chosen for explicit state-machine control and native human-in-the-loop interrupts (required for the keyword-selection and application-review gates). Works against any OpenAI-compatible local LLM endpoint (Ollama/vLLM) — not tied to a specific model provider.

### 4.2 Tool Access: MCP
All tool access (job search sources, MongoDB, LaTeX rendering, browser control) is wrapped as MCP servers, decoupling tools from the orchestration framework. This means swapping LangGraph for CrewAI/AutoGen later wouldn't require rewriting tool integrations.

### 4.3 A2A — Not Used in v1
A2A (Agent2Agent protocol) is useful when agents need to run as independently scalable services. At single-user scale, in-process LangGraph nodes calling MCP tools are simpler and sufficient. Revisit only if the Application Agent needs to run as an always-on service on separate hardware.

### 4.4 Chrome Extension ↔ Backend
```
┌───────────────────────┐      HTTP (localhost)      ┌──────────────────────────┐
│  Chrome Extension       │ ─────────────────────────▶ │  Local Backend (FastAPI)   │
│  - content script         │ ◀───────────────────────── │  - job_id → tailored resume│
│    (detects & fills form)  │   JSON: field answers,     │  - Q&A answer bank           │
│  - popup UI                  │   resume file path           │  - JD / gap context           │
│  - background service worker  │                                 │                                  │
└───────────────────────┘                             └──────────────────────────┘
```

---

## 5. Deployment Architecture

- **Compute:** Local machine (Mac) running Ollama (dev) or vLLM (heavier concurrent use) for LLM inference
- **Databases:** Local MongoDB (native install, no Docker needed) + MongoDB Atlas free tier
- **Backend:** FastAPI, run locally (`localhost` only, no public exposure by default)
- **Frontend:** Local dashboard — Streamlit/Gradio for MVP, optional React upgrade later
- **Browser layer:** Chrome extension, loaded unpacked in developer mode (no Chrome Web Store publish needed)
- **Queue/scheduling:** Redis + Celery for scheduled discovery runs
- **CI/CD:** GitHub Actions for tests/linting; no production deployment target beyond your own machine

```
┌─────────────────────────────── Your Mac ───────────────────────────────┐
│                                                                          │
│  Ollama/vLLM (local LLM)     FastAPI backend      Local MongoDB          │
│  Redis + Celery              Chrome (extension)   Streamlit/Gradio dash  │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────┘
                                    │ vector search calls only
                                    ▼
                          MongoDB Atlas (free M0 tier)
```

---

## 6. Sequence Flows

### 6.1 Daily Job Discovery
```
Scheduler (Celery beat) → Job Discovery Agent → [Google/SerpAPI, Indeed MCP, LinkedIn]
   → normalize + dedup → write to local `jobs`
```

### 6.2 JD Match → Keyword Selection → Tailor
```
User selects a job → JD Match Agent extracts keywords, embeds JD (Atlas),
   runs $vectorSearch, computes Present/Missing → writes to local `matches`
   → Orchestrator pauses (interrupt) → Dashboard shows Present/Missing lists
   → User selects keywords → Resume Tailor Agent renders .tex via Jinja2
   → .tex saved locally, path written to `applications`
```

### 6.3 Apply Flow
```
User opens ATS page in Chrome → Extension popup shows job context
   → Content script detects fields → Background worker fetches answers
     from local backend → Fields auto-filled + highlighted
   → User attaches .tex (manual, 2 clicks) → User reviews → User clicks Submit
   → Extension/dashboard updates `applications.status` = "Applied"
   → Tracking Agent logs event, syncs Google Sheet
```

---

## 7. Technology Stack Summary

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| Tool protocol | MCP (self-hosted MCP servers), MongoDB MCP Server |
| LLM serving | Ollama (dev) / vLLM (production-like) |
| Models | Qwen2.5-32B+/Llama 3.3-70B (orchestration, tailoring); smaller Qwen2.5-7B/14B (discovery, scoring); BGE-M3/nomic-embed-text (embeddings) |
| Database — structural | Local MongoDB (native install) |
| Database — vector | MongoDB Atlas (free M0 tier) |
| Backend | FastAPI (Python) |
| Frontend | Streamlit/Gradio (MVP) → React+TS (later, optional) |
| Browser automation (discovery) | Playwright |
| Application autofill | Custom Chrome Extension (Manifest V3) |
| Resume templating | Jinja2 (custom delimiters) over existing `base_resume.tex` |
| Cache/queue | Redis + Celery |
| Eval/observability | Langfuse or Phoenix (Arize) — self-hosted |

---

## 8. Security & Privacy Considerations

- All resume/JD/PII data processed by local LLMs — never sent to third-party hosted AI APIs
- Only vector embeddings (not raw resume text) need live in Atlas — minimize what leaves the local machine
- Local dashboard/backend bound to localhost by default — no public exposure
- No stored credentials for ATS platforms — the Chrome extension relies on your already-authenticated session, never handles your login credentials directly
