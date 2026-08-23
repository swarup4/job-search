# Agentic AI Job Search Platform — Project Roadmap

**Working name:** JobPilot (rename freely)
**Owner:** Swarup Saha
**Core idea:** A multi-agent system that discovers relevant jobs, tailors your resume per JD, and manages applications end-to-end — essentially productizing the workflow you already run manually via `job-search-genai`, `resume-maker`, and `hr-contact-prospecting`.

---

## 1. Vision

A personal job-search co-pilot — **single-user, just for you, not a multi-tenant product** — where specialized agents collaborate under one orchestrator:

- Find jobs that actually match your profile (not keyword noise)
- Tailor resume + cover letter per JD automatically
- Prepare and (with your approval) submit applications
- Track status, follow-ups, and outcomes in one dashboard

**Important framing decision up front:** true "fire-and-forget auto-apply" across job boards runs into two hard walls — (a) most boards' Terms of Service prohibit automated form submission/scraping, and (b) logins, CAPTCHAs, and multi-step ATS forms make full automation brittle and easy to get flagged/banned on your own account. So the roadmap below treats the **Application Agent as semi-autonomous by default**: it fills and stages the application, you get a one-click review/approve step, then it submits. You can loosen this later per-platform where official APIs exist (e.g., Indeed via MCP, LinkedIn Easy Apply where permitted).

---

## 2. Agent Architecture

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
   │                  │ │ Agent     │ │                │ │ (semi-auto)  │ │ Agent       │
   └─────────────────┘ └───────────┘ └───────────────┘ └──────────────┘ └─────────────┘
          │                   │              │                  │               │
          ▼                   ▼              ▼                  ▼               ▼
     Job listings +   Match scores +   Tailored .tex     Staged / submitted   Status + email
     embeddings        keyword gaps     files (per job)   applications         events
     (local + Atlas)   (local Mongo)    (local Mongo)     (local Mongo)        (local Mongo)
```

### 2.1 Job Discovery Agent
- **Job:** Pull fresh listings matching your target roles/locations.
- **Sources:** Google Custom Search / SerpAPI for "site:linkedin.com/jobs" style queries, Indeed MCP connector (you already have this), Naukri/LinkedIn scraping (reuse your `linkedin-hiring-scraper` skill), company career pages via RSS/sitemap where available.
- **Output:** Normalized job record — title, company, location, JD text, source URL, posted date, dedup hash.
- **Guardrail:** Respect `robots.txt` and rate limits; prefer official APIs/MCP over scraping wherever one exists.

### 2.2 JD Match/Score Agent
- **Job:** Extract technical keywords from the JD, diff them against your resume's skill list, and score fit — similar to the ATS scoring you already do manually.
- **Workflow (interactive, not fully automatic):**
  1. Extract technical keywords/tech-stack terms from the uploaded JD (LLM structured extraction — skills, tools, frameworks, certifications mentioned).
  2. Diff against your current resume's skill list → produce a **Present** list and a **Missing** list.
  3. Show both lists to you; you **select** which missing keywords to incorporate (protects the "never fabricate" rule — you're consciously choosing what to add, not the agent silently inserting things).
  4. Your selections are passed to the Resume Tailor Agent (2.3) as the tailoring instruction.
- **Approach:** Embed JD + resume sections (local embedding model) for semantic similarity, plus LLM-based keyword extraction/critique.
- **Output:** Ranked shortlist with match %, Present/Missing keyword lists, and flagged risks (e.g., "asks for 5+ yrs Java, your resume shows none — flag, don't fabricate").

### 2.3 Resume Tailor Agent
- **Job:** Takes your selected keywords (from 2.2) and regenerates a JD-specific `.tex` resume file — reuses your existing `resume-maker` template/custom-command approach (`\certrow`, `\jobtitle`, etc.).
- **Current scope: outputs a `.tex` source file only** — PDF compilation is a separate, later step, not bundled into this agent yet.
- **Guardrail (already a rule you follow):** Never fabricate skills/experience beyond what you explicitly selected; flag anything you didn't select rather than quietly adding it.
- **Templating approach — library options beyond raw string substitution:**

| Library | What it does | Fit |
|---|---|---|
| **Jinja2** (with custom delimiters, e.g. `\VAR{}` / `\BLOCK{}` instead of default `{{ }}` to avoid clashing with LaTeX braces) | General templating engine — fill placeholders in a `.tex` template with data | **Best fit** — closest to your existing `base_resume.tex` + custom-command structure, minimal rework needed |
| **PyLaTeX** | Python OOP API to build `.tex` documents programmatically | Better for building from scratch than filling an existing template |
| **TexSoup** | Parses/edits existing `.tex` files as a syntax tree | Useful for surgical edits to specific sections without full re-render |
| **pylatexenc** | Converts between LaTeX and Unicode/plain text | Utility, not a templating solution |

- **Output:** Tailored `.tex` file, versioned per job ID. (PDF compilation step to be added later once the `.tex` workflow is solid.)

### 2.4 Application Agent (semi-autonomous)
- **Job:** Fill the application form and attach tailored resume, populate answers to common screening questions from a saved Q&A bank.
- **How it fills forms — Chrome extension, not a standalone automated browser.** See Section 6 for full detail and reasoning; short version: a Chrome extension running in your real logged-in session is more reliable and far less likely to trigger anti-bot detection than a separate Playwright-controlled browser, and it keeps the human-approval gate physically built in (you click Submit yourself).
- **Human-in-the-loop gate:** Always pause at "review the filled form" before you hit submit — non-negotiable, and naturally enforced since it's your own browser.
- **Later phase:** Auto-submit only for platforms with official application APIs (fewer ToS/CAPTCHA risks).

### 2.5 Tracking & Follow-up Agent
- **Job:** Maintain the pipeline (Applied → Viewed → Interview → Offer/Rejected), draft follow-up emails at configurable intervals, sync to your existing Google Sheet tracker.
- **Output:** Dashboard status + reminder notifications.

### 2.6 Orchestrator (Supervisor)
- **Job:** LangGraph state machine routing between agents, holding shared state (profile, job queue, in-flight applications), handling retries/human-approval interrupts.

---

## 3. Tech Stack (fully local / self-hosted, framework-agnostic)

### 3.1 Local LLM serving

| Option | Why pick it |
|---|---|
| **Ollama** | Easiest setup, good model catalog, decent for dev + small-scale prod |
| **vLLM** | Much higher throughput/concurrency, OpenAI-compatible API, better if multiple agents call the LLM in parallel |
| **LM Studio** | Good for local dev/testing with a GUI, not meant for server workloads |

Recommendation: **Ollama for local dev**, **vLLM behind a FastAPI gateway for anything resembling production**, both expose OpenAI-compatible `/v1/chat/completions`, so your agent code doesn't need to change between them.

### 3.2 Model choice — this matters more than the framework

Agentic workflows live and die on **reliable structured tool calling**, not raw reasoning power. Not every local model is good at this. Practical picks (as of your local hardware capacity):

| Task | Model options | Notes |
|---|---|---|
| Orchestration / tool-calling agents | **Qwen2.5-32B/72B-Instruct**, **Llama 3.3-70B-Instruct**, **Hermes-3** | Strong, well-tested function-calling support |
| Lightweight sub-agents (discovery, scoring) | **Qwen2.5-14B/7B-Instruct**, **Mistral-Small** | Cheaper/faster, fine for narrow, well-scoped tasks |
| JD matching / embeddings | **BGE-M3**, **nomic-embed-text**, **Qwen3-Embedding** | Run via Ollama/vLLM or a dedicated embedding server |
| Resume tailoring (needs strong instruction-following + low hallucination) | **Qwen2.5-32B+** or **Llama 3.3-70B** | Smaller models tend to drift or overstate skills — riskier for your "never fabricate" rule |

Rule of thumb: use your **strongest available local model for the Orchestrator + Resume Tailor Agent** (highest stakes for accuracy), and smaller/faster models for Discovery and Tracking agents which do more mechanical work.

**Hardware reality check:** 70B-class models need ~40GB+ VRAM at 4-bit quant (e.g., dual 24GB GPUs, or one 48GB card). If you're on a single consumer GPU (12–24GB), plan around the 7B–32B range with 4-bit/AWQ/GGUF quantization — still very workable for this use case, just test tool-calling reliability early since smaller quantized models are where it degrades first.

### 3.3 Agent framework — pick based on control vs. speed-to-build

| Framework | Fit for this project | Trade-off |
|---|---|---|
| **LangGraph** | Best if you want explicit state machine control + human-in-the-loop interrupts (needed for your "approve before submit" gate) — and it works fine with any OpenAI-compatible local endpoint, not just Claude/OpenAI | More boilerplate than CrewAI |
| **CrewAI** | Fastest to prototype role-based agents (Discovery, Matcher, Tailor, Applicator as "crew members") | Less fine-grained control over interrupts/state than LangGraph |
| **AutoGen / AG2** | Strong for conversational multi-agent patterns, good local-model support | Slightly less mature human-in-the-loop primitives than LangGraph |
| **A2A (Agent2Agent protocol)** | Use this as the *inter-agent communication layer* if you want agents to be independently deployable services (e.g., Application Agent as its own microservice another orchestrator can call) rather than in-process function calls | Adds infra complexity — worth it only if agents need to run as separate services/scale independently |
| **MCP** | Use as the *tool-access layer* regardless of framework — wrap Google/Indeed/LinkedIn search, resume PDF generation, Playwright browser control, DB access as MCP servers, so any agent (or future framework swap) can call them uniformly | Adds a thin server layer per tool, but decouples tools from orchestration logic entirely |

**Recommended combo for this project:** **LangGraph** for orchestration + human-approval gates, **MCP** for tool access (job search, resume rendering, browser automation, DB), and optionally **A2A** later if you want the Application Agent to run as an independently scalable service. This gives you framework flexibility — MCP-wrapped tools work the same if you later swap LangGraph for CrewAI or AutoGen.

### 3.4 Rest of the stack

| Layer | Choice | Why |
|---|---|---|
| Tool protocol | **MCP** (self-hosted MCP servers) | Wrap job search, resume rendering, browser automation as MCP tools |
| Eval/observability | **Langfuse** (self-hosted) or **Phoenix (Arize)** | Local alternative to LangSmith — traces, evals, works with any LLM |
| Backend API | **FastAPI (Python)** | Matches your stack |
| Frontend | **React + TypeScript** | Dashboard for shortlist review, approve-to-apply, pipeline tracking |
| Database — vector search | **MongoDB Atlas (free M0 tier)** | Hosts `$vectorSearch`-indexed collections (JD embeddings, resume-chunk embeddings) — sidesteps the macOS `mongot` limitation entirely since Atlas manages it for you. Only the data that actually needs semantic search lives here. |
| Database — structural data | **MongoDB (local, native install — no Docker/`mongot` needed)** | Everything else: profile, job metadata, applications, tracking/events, Q&A answer bank. Stays fully local/private; only vector-search-relevant data goes to Atlas. |
| Data access for agents | **MongoDB MCP Server** | Official MCP server for MongoDB — exposes both the local and Atlas instances as tools your agents (via LangGraph) can query directly, rather than hand-rolling DB clients per agent |
| Cache/queue | **Redis + Celery** | Scheduled discovery runs, async agent tasks |
| Browser automation (discovery only) | **Playwright** | Scraping/searching job listings — no login sensitivity, automation fingerprint doesn't matter here |
| Application form autofill | **Custom Chrome Extension (Manifest V3)** | Runs in your real logged-in session — see Section 6 |
| Resume rendering | **LaTeX pipeline (your existing `resume-maker` skill logic, adapted)** | Already production-tested by you |
| Auth/deploy | **Docker Compose on your own machine/homelab (or single VM)**, GitHub Actions CI/CD | Single-user — no need for multi-tenant auth, SSO, or user management; a simple local admin password (or none, if it never leaves your LAN) is enough |

---

## 4. Data Model (split store: Atlas for vector, local MongoDB for everything else)

### 4.1 MongoDB Atlas (free M0 tier) — vector-search collections
- `jobs.jd_embedding` — JD text + embedding vector, indexed via `$vectorSearch`, for semantic JD↔resume matching
- `profile.resume_chunks` — resume sections + embeddings, same index type

Only the data that actually needs semantic similarity search lives here — keeps you well within the free-tier 512MB cap.

### 4.2 Local MongoDB (native install, no Docker needed) — structural data
- `profile` — resume master data, skills, certs, preferences (roles, locations, salary band)
- `jobs` — discovered listings: source, JD text, dedup hash, posted date (raw text; the embedding itself lives in Atlas alongside a shared `job_id`)
- `matches` — job_id ↔ profile match score, Present/Missing keyword lists, gap analysis
- `applications` — job_id, tex_version, cover_letter, status, staged/submitted timestamp, approval_by_user flag
- `events` — status changes, follow-up emails sent, interview notes

### 4.3 Feeding data to the agents
Use the **MongoDB MCP Server** (official MongoDB MCP integration) to expose both the local instance and the Atlas cluster as tools your LangGraph agents call directly — the JD Match/Score Agent (2.2) queries Atlas for `$vectorSearch` similarity, while the other agents read/write structural data against the local instance. One MCP layer, two backing databases, `job_id` as the join key between them.

---

## 5. Roadmap (Phased, ~10 weeks)

### Phase 0 — Foundation (Week 1)
- Define target role/location profile schema
- Set up local MongoDB (native install — structural data) + MongoDB Atlas free tier (vector-search collections) + Redis, repo scaffolding, CI/CD skeleton
- Create `$vectorSearch` index on Atlas `jobs.jd_embedding`
- Set up MongoDB MCP Server to expose both instances as agent tools
- Stand up LangGraph project skeleton with a no-op orchestrator

### Phase 1 — Job Discovery Agent (Weeks 2–3)
- Integrate Indeed MCP + SerpAPI/Google CSE
- Adapt `linkedin-hiring-scraper` skill into an agent tool
- Dedup + normalize + store pipeline
- Scheduled daily run (Celery beat / Azure Function timer)

### Phase 2 — JD Match & Resume Tailor Agents (Weeks 3–4)
- JD keyword extraction (LLM structured extraction) + Present/Missing diff against your resume
- Build the keyword-selection UI step (you pick which missing keywords to incorporate)
- Wrap `resume-maker` template as a Jinja2-based `.tex` generator (custom delimiters to avoid LaTeX brace clashes) taking your selections as input
- Add the "no fabrication" guardrail as a hard system rule with test cases — only selected keywords get incorporated
- Scope for this phase: `.tex` output only; PDF compilation deferred to a later phase

### Phase 3 — Application Agent, semi-auto (Weeks 5–6)
- Build the Chrome extension autofill companion (see Section 9) targeting 2–3 ATS platforms first (Workday, Greenhouse, Lever — more standardized DOMs)
- Field-matching heuristics + LLM fallback for ambiguous fields
- Q&A bank for common screening questions

### Phase 4 — Tracking Dashboard (Weeks 6–7)
- React dashboard: shortlist review, approve-to-apply, pipeline kanban
- Google Sheet sync (reuse existing tracker logic)
- Follow-up email drafts on interval triggers

### Phase 5 — Multi-agent Orchestration (Weeks 7–8)
- Wire all agents into the LangGraph supervisor with shared state
- Add retry/error handling, human-interrupt nodes at approval points

### Phase 6 — Eval & Guardrails (Weeks 8–9)
- Ragas eval suite: match-score accuracy, resume-tailor faithfulness (no fabricated skills), application form-fill accuracy
- LangSmith tracing dashboards for debugging agent runs

### Phase 7 — Deploy & Polish (Weeks 9–10)
- Dockerize, deploy to Azure App Service
- Rate limiting, secrets management, basic auth for the dashboard
- MVP demo + iterate

---

## 6. Chrome Extension — Autofill Companion

**Short answer: yes, build one.** For a single-user tool, it's the more practical and more reliable choice than a standalone automated browser for the actual application-filling step.

### 6.1 Why an extension instead of Playwright for this step
- Uses your **real, already-authenticated browser session** — no re-login, no cookie export/import, no CAPTCHA re-triggering from a "new" automated session.
- **Lower bot-detection risk.** ATS platforms and LinkedIn actively check for automation signals (`navigator.webdriver`, headless flags, unusual timing patterns). A real Chrome session with a real extension doesn't carry these red flags the way a Playwright-driven browser can, even in non-headless mode.
- **Human-approval gate is physically built in** — the extension fills fields, but you're the one looking at the page and clicking Submit. This satisfies the "never auto-submit without review" rule from Section 2.4 by construction, not just by convention.
- Works across whatever site you're currently on without needing a maintained Playwright script per ATS vendor — you build one field-detection layer and reuse it everywhere.

### 6.2 Architecture

```
┌───────────────────────┐      HTTP (localhost)      ┌──────────────────────────┐
│  Chrome Extension       │ ─────────────────────────▶ │  Local Backend (FastAPI)   │
│  - content script         │ ◀───────────────────────── │  - job_id → tailored resume│
│    (detects & fills form)  │   JSON: field answers,     │  - Q&A answer bank           │
│  - popup UI                  │   resume file path           │  - JD / gap context           │
│  - background service worker  │                                 │                                  │
└───────────────────────┘                             └──────────────────────────┘
```

- **Content script** runs on the job application page, scans the DOM for form fields (inputs, selects, textareas), matches them to known fields (name, email, phone, LinkedIn URL, "years of experience," common screening questions) using label text / `aria-label` / `placeholder` heuristics.
- **Background service worker** calls your local FastAPI backend (`http://localhost:PORT`) with the current job's context (job_id passed via URL or a small popup selector) and gets back the answer payload.
- **Popup UI** shows you what's about to be filled before it happens (or highlights filled fields in the page itself), giving you a last look before you scroll down and hit Submit yourself.
- **Resume/cover letter upload:** file inputs can't be set programmatically via JavaScript for security reasons — this is true for extensions and Playwright alike. Practical fix: the extension opens the correct tailored PDF's folder location or copies the file path to your clipboard so you drag-and-drop or browse-select it in two clicks. This is a fine manual step for single-user use.

### 6.3 Build scope
- **Manifest V3**, content script + background service worker + small popup (plain HTML/JS is enough — no need for a framework given the tiny surface area)
- Field-matching logic: start with a rules/heuristics layer (label text matching, common ATS field name patterns for Workday/Greenhouse/Lever/LinkedIn Easy Apply), fall back to an LLM call (your local model) for ambiguous fields — send the field's label + surrounding DOM text, get back which answer-bank entry it maps to
- No need to publish to the Chrome Web Store — load it as an unpacked extension in developer mode since it's just for you

### 6.4 Where this fits in the roadmap
Folds into **Phase 3 (Weeks 5–6)** of Section 5 (Roadmap) — this *is* what Phase 3 now builds, replacing the earlier Playwright-form-fill idea.

---

## 7. What Being Single-User Simplifies

Worth calling out since it changes real build effort, not just deployment:

- **No auth/tenant system** — skip user accounts, RBAC, org-scoping on every table. A single config file with your profile + preferences is enough.
- **No multi-tenant DB design** — drop `user_id`/`tenant_id` columns everywhere; schemas stay flat and simple.
- **Scale targets are trivial** — you're talking dozens of jobs/day, not thousands of concurrent users. Local MongoDB for structural data plus the Atlas free tier for vector search comfortably handles this; no need for horizontal scaling, load balancers, or sharding.
- **A2A becomes optional, not necessary** — the "independently scalable microservice" argument for A2A mainly matters at multi-tenant scale. For single-user, in-process LangGraph nodes calling MCP tools is simpler and sufficient. Keep A2A in your back pocket only if you specifically want the Application Agent running as a separate always-on service (e.g., on a different machine from your main GPU box).
- **Dashboard can be minimal** — one page, no per-user views, no permissions logic. Could even start as a Streamlit/Gradio app before investing in a full React frontend.
- **Human-approval gate is just "you"** — no notification/assignment system needed; a simple pending-queue in the UI you check once a day is enough.

This also means the MVP scope (Section 8) is realistically faster than a 4-week estimate — likely 2–3 weeks given the removed auth/multi-tenant overhead.

## 8. MVP Scope (if you want to move faster)

Cut to just: Job Discovery Agent → JD Match Agent → Resume Tailor Agent → manual apply (no Application Agent yet), surfaced through a simple dashboard. This alone would already beat your current manual workflow and is achievable in ~4 weeks solo.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Job board ToS violations from scraping/auto-submit | Prefer official APIs/MCP; keep Application Agent human-approved by default |
| CAPTCHA/anti-bot blocks | Limit automation to ATS platforms with standardized, automatable forms; don't force scale on hostile sites |
| Resume fabrication to boost match % | Hard-coded guardrail + eval tests; agent must flag gaps, never invent experience |
| Over-applying / spammy outreach | Cap daily applications, require review gate, dedupe aggressively |
| Data privacy (resume/PII in DB) | Encrypt at rest, restrict access, don't log full resume text in traces |
| Local model unreliable tool-calling / structured output | Test tool-calling accuracy per model before committing; use JSON-mode/grammar-constrained decoding (e.g., via vLLM guided decoding or Outlines) as a fallback for critical agents |

---

## 10. Success Metrics

- Time from "job posted" → "tailored resume ready": target < 5 min
- Match-score precision (spot-checked against your own judgment)
- Applications submitted per week vs. manual baseline
- Interview conversion rate before/after using the platform

---

*Next step: pick your local model + serving setup (Ollama for dev is the fastest start), confirm GPU/VRAM budget, and I can help scaffold the LangGraph + MCP project structure and get the first agent (Job Discovery) running against your local endpoint.*
