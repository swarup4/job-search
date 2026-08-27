# Project Roadmap & Backlog

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | v1.1 — dashboard UI implemented, backend not started |
| **Updated** | 2026-08-24 |

---

## 1. Roadmap (10 phases, single-user scope)

Phases 0 and 1 are complete; Phase 2 is partly done — the REST API and data layer are built, the
infrastructure around them is not. The week estimates on Phases 2–9 count from the start of Phase 2, so
the original ~8–10 week figure still describes the work that remains.

### Phase 0 — Architecture & Planning ✅ complete
- Product requirements, functional/non-functional spec, system design
- Six-screen UI/UX definition and end-to-end user flows
- Phased roadmap, epics, backlog IDs
- Delivered as docs [01](01-PRD-Product-Requirements-Document.md)–[05](05-Roadmap-Backlog.md)

### Phase 1 — Dashboard UI ✅ complete
- All screens built in Next.js + Tailwind, running on JSON fixtures
- Pipeline board · job search · shortlist · job details · staged applications · my details · settings
- Keyword Selection screen — starts with nothing checked, per FR-2.5
- Resume Preview screen — Preview / Diff / Source tabs and a `.tex` download
- `templates/base_resume.tex` written, Jinja2 render verified (never TeX-compiled)
- **No backend behind any of it** — see [Implementation status](#implementation-status)

### Phase 2 — Foundation (Week 1) 🚧 partial
- ✅ Define target role/location profile schema — `profile.preferences`, see [doc 06](docs/06-Data-Model-ER.md)
- ✅ FastAPI app + Beanie ODM over local MongoDB — six modules, eight collections, 28 endpoints over 20 paths
- ✅ Local MongoDB structural store, with indexes created at startup
- ⬜ MongoDB Atlas free tier + `$vectorSearch` index on `jd_embedding`
- ⬜ Redis + Celery
- ⬜ Set up MongoDB MCP Server *(superseded — structural data goes through `jobpilot_api` over HTTP;
  see the FR-8.1 note in doc 02)*
- ⬜ Stand up LangGraph project skeleton with a no-op orchestrator
- ⬜ Pick and validate local LLM (Ollama for dev) — confirm tool-calling reliability

**Not done and load-bearing:** `server/` has no tests. They were written and removed on request
(2026-08-24), so the guardrail stories below cannot meet the §4 Definition of Done until they
return — the enforcement is in the code, but the proof is not.

### Phase 3 — Job Discovery Agent (Weeks 2–3)
- Integrate Indeed MCP + SerpAPI/Google CSE
- Adapt `linkedin-hiring-scraper` skill into an agent tool
- Dedup + normalize + store pipeline into local MongoDB
- Scheduled daily run via Celery beat

### Phase 4 — JD Match & Resume Tailor Agents (Weeks 3–4)
- JD keyword extraction + Present/Missing diff against resume
- Wire the existing Keyword Selection screen to real match data
- Jinja2-based `.tex` generator driven by `ai/mcp_servers/latex/`
- "No fabrication" guardrail — only selected keywords incorporated
- Scope: `.tex` output only, no PDF compile yet

### Phase 5 — Application Agent, Chrome Extension (Weeks 5–6)
- Build extension (Manifest V3): content script, background worker, popup
- Field-matching heuristics for 2–3 ATS platforms (Workday, Greenhouse, Lever)
- Local FastAPI backend serving job context/Q&A answers
- Manual resume-attach flow (file path copy)

### Phase 6 — Tracking & Follow-up (Weeks 6–7)
- Replace the dashboard's JSON fixtures with `server` API calls
- Google Sheet sync
- Follow-up draft generation on interval triggers

### Phase 7 — Multi-agent Orchestration (Weeks 7–8)
- Wire all agents into LangGraph supervisor with shared state
- Implement human-approval interrupts (keyword selection, application review)
- Retry/error handling for failed agent steps

### Phase 8 — Eval & Guardrails (Weeks 8–9)
- Eval suite (Langfuse/Phoenix): match-score accuracy, resume-tailor faithfulness, form-fill accuracy
- Guardrail test cases: no-fabrication, no-auto-submit

### Phase 9 — Polish & Daily Use (Weeks 9–10)
- Bug fixes from real daily usage
- Q&A answer bank refinement
- Optional: PDF compilation step, cover letter generation (stretch goals — see Backlog)

### Implementation status

The dashboard UI was built ahead of the backend. Eleven screens exist and render, every one backed
by a JSON fixture in `app/web/src/data/`. `server/` and `ai/` are still empty directories, so
nothing runs end-to-end and **no story below meets the §4 Definition of Done.**

| Built | Backed by |
|---|---|
| Pipeline board · Shortlist · Staged Applications · Job Search · Job Details · My Details · Settings | `board.json` `search.json` `applications.json` `profile.json` `settings.json` |
| Keyword Selection — starts with nothing checked, per FR-2.5 | `matches.json` |
| Resume Preview — Preview / Diff / Source tabs, `.tex` download | `resume.json` + `templates/base_resume.tex` |
| Login · Signup | nothing — no auth service exists |

**Three deviations from this document, recorded deliberately:**

1. **Next.js, not Streamlit/Gradio.** The dashboard phase and TRACK-1 named Streamlit or Gradio, and TRACK-7
   deferred a React frontend to v2. The dashboard was built directly in Next.js + Tailwind, matching
   the stack in `CLAUDE.md` and doc 03. TRACK-7 is therefore **closed, not deferred**, and the
   Streamlit/Gradio path was never taken.
2. **`templates/base_resume.tex` exists and renders, but nothing in `ai/` drives it.** The Jinja2
   render (custom `\VAR{}`/`\BLOCK{}` delimiters) was validated with a throwaway script, not by
   `ai/mcp_servers/latex/`. TAILOR-1 stays Partial, and the template has **never been compiled by a
   TeX engine** — its LaTeX validity is unverified.
3. **Login and Signup screens exist**, which PRD §4, SRS §42 and `.claude/rules/server-api.md` all
   rule out. They are interface only and authenticate nothing. Either those docs get amended or the
   screens get removed — tracked as TRACK-12.

**Note:** given single-user scope removes auth/multi-tenant overhead, MVP (Phases 2–4, manual apply) is realistically achievable in **2–3 weeks** if you want to start using it before the full system is built.

---

## 2. Product Backlog (Epics → Stories)

**Status legend.** `UI done` — the screen is built and renders against a JSON fixture; there is
no backend behind it, so it does **not** meet the §4 Definition of Done. `Partial` — some
artefacts exist, story incomplete. `—` — not started.

### Epic 1: Infrastructure & Data Layer
| ID | Story | Priority | Status |
|---|---|---|---|
| INFRA-1 | Set up local MongoDB + Atlas free tier + `$vectorSearch` index | Must | Partial — local store done, Atlas not started |
| INFRA-2 | Set up MongoDB MCP Server | Must | Superseded — see FR-8.1 note in doc 02 |
| INFRA-3 | Set up Redis + Celery for scheduling | Must | — |
| INFRA-4 | Validate local LLM tool-calling reliability (Ollama, target model) | Must | — |
| INFRA-5 | Set up Langfuse/Phoenix for eval/observability | Should | — |
| INFRA-6 | CI/CD via GitHub Actions (lint/test on push) | Could | — |
| API-1 | FastAPI app shell — thin `main.py`, localhost bind, CORS for web + extension | Must | Done |
| API-2 | Beanie documents for all eight local collections, `ObjectId` keys | Must | Done |
| API-3 | `job` module — create with dedup-hash check, list by status, shortlist | Must | Done |
| API-4 | `match` module — write score/keywords, record the user's selection | Must | Done |
| API-5 | `resume` module — store versioned `.tex` + selection set, reject unselected keywords | Must | Done |
| API-6 | `application` module — stage, record fill, status transitions, answer bank | Must | Done |
| API-7 | `event` + `profile` modules — audit log, profile, RAG chunk-text hop | Must | Done |
| API-8 | Test suite for the API and its guardrails | Must | Removed on request — see Phase 2 note |

### Epic 2: Job Discovery
| ID | Story | Priority | Status |
|---|---|---|---|
| DISC-1 | Integrate Indeed MCP connector | Must | — |
| DISC-2 | Integrate Google CSE/SerpAPI search | Must | — |
| DISC-3 | Adapt `linkedin-hiring-scraper` skill as agent tool | Should | — |
| DISC-4 | Dedup logic (content hash) | Must | — |
| DISC-5 | Scheduled daily run (Celery beat) | Must | — |
| DISC-6 | Naukri / company career page sources | Could | — |

### Epic 3: JD Match & Keyword Selection
| ID | Story | Priority | Status |
|---|---|---|---|
| MATCH-1 | LLM structured keyword extraction from JD | Must | — |
| MATCH-2 | Embed JD → Atlas `$vectorSearch`, compute match score | Must | — |
| MATCH-3 | Present/Missing keyword diff logic | Must | — |
| MATCH-4 | Risk-flag detection (seniority mismatch, etc.) | Should | — |
| MATCH-5 | Keyword Selection UI (checkbox screen) | Must | UI done |

### Epic 4: Resume Tailoring
| ID | Story | Priority | Status |
|---|---|---|---|
| TAILOR-1 | Jinja2 template wrapper over `base_resume.tex` (custom delimiters) | Must | Partial |
| TAILOR-2 | Incorporate only user-selected keywords | Must | — |
| TAILOR-3 | Version `.tex` files per job ID | Must | — |
| TAILOR-4 | Resume Tailor Preview screen (diff view) | Should | UI done |
| TAILOR-5 | (Stretch) PDF compilation step | Won't (v1) | — |
| TAILOR-6 | (Stretch) Cover letter generation | Won't (v1) | — |

### Epic 5: Application Autofill (Chrome Extension)
| ID | Story | Priority | Status |
|---|---|---|---|
| APPLY-1 | Extension scaffold (Manifest V3, content script, popup) | Must | — |
| APPLY-2 | Field-detection heuristics (label/ARIA/placeholder matching) | Must | — |
| APPLY-3 | LLM fallback for ambiguous field matching | Should | — |
| APPLY-4 | Local FastAPI backend (job context + Q&A bank) | Must | — |
| APPLY-5 | Highlight filled fields for review | Must | — |
| APPLY-6 | Manual resume-attach flow (copy file path) | Must | — |
| APPLY-7 | Workday/Greenhouse/Lever field-pattern support | Should | — |
| APPLY-8 | LinkedIn Easy Apply support | Could | — |

### Epic 6: Tracking & Dashboard
| ID | Story | Priority | Status |
|---|---|---|---|
| TRACK-1 | Pipeline board (Next.js) | Must | UI done |
| TRACK-2 | Job Shortlist / Match Review screen | Must | UI done |
| TRACK-3 | Staged Applications screen | Must | UI done |
| TRACK-4 | "Pending your review" banner (approval-gate surface) | Must | UI done |
| TRACK-5 | Follow-up draft generation on interval | Should | — |
| TRACK-6 | Google Sheet sync | Should | — |
| TRACK-7 | React frontend — built in v1 instead of Streamlit/Gradio | Must | UI done |
| TRACK-8 | Job Search screen (multi-field search + facets) | Should | UI done |
| TRACK-9 | Job Details screen | Should | UI done |
| TRACK-10 | My Details (profile) screen | Should | UI done |
| TRACK-11 | Settings screen | Should | UI done |
| TRACK-12 | Login / Signup screens — conflict with PRD §4, no auth service | Out of scope | UI done |

### Epic 7: Orchestration & Guardrails
| ID | Story | Priority | Status |
|---|---|---|---|
| ORCH-1 | LangGraph supervisor wiring all agents | Must | — |
| ORCH-2 | Human-approval interrupts (keyword selection, application review) | Must | — |
| ORCH-3 | Retry/error handling per agent step | Must | — |
| ORCH-4 | No-fabrication guardrail test cases | Must | — |
| ORCH-5 | No-auto-submit guardrail test cases | Must | — |

---

## 3. Sprint Breakdown (2-week sprints, ~5 sprints)

| Sprint | Focus | Backlog Items |
|---|---|---|
| Sprint 1 (Wks 1–2) | Foundation + Discovery start | INFRA-1–4, DISC-1–5 |
| Sprint 2 (Wks 3–4) | Match + Tailor | MATCH-1–5, TAILOR-1–4 |
| Sprint 3 (Wks 5–6) | Application Extension | APPLY-1–7 |
| Sprint 4 (Wks 7–8) | Dashboard + Orchestration | TRACK-1–6, ORCH-1–3 |
| Sprint 5 (Wks 9–10) | Guardrails + Polish | ORCH-4–5, INFRA-5, real-usage bug fixes |

**Sprint order was not followed.** The Epic 6 screens plus MATCH-5 and TAILOR-4 were built as
Phase 1, ahead of every sprint below, so the UI is waiting on the backend rather than the
reverse. Sprint 4's dashboard work is already done; what remains there is wiring those screens
to `server` (Phase 6).

---

## 4. Definition of Done (per story, general)

- Functionality works end-to-end against local LLM + real (or realistic test) data
- No hard-coded secrets; config via environment variables
- Guardrail-relevant stories (fabrication, auto-submit) have explicit test cases proving the guardrail holds
- Manually exercised by the user (Swarup) at least once in the actual daily workflow before marked Done

---

## 5. Stretch / Backlog (Won't-have in v1, candidates for v2)

- PDF compilation of tailored `.tex` resumes — the Resume Preview screen has the slot for it
  (a locked tab was replaced by a `.tex` download); needs a TeX engine and an amendment to
  invariant 5 / FR-4.4
- Cover letter generation
- LinkedIn Easy Apply full support
- A2A-based Application Agent as an independently scalable service
- Multi-device sync (if ever needed — would require revisiting the single-user Atlas-only vector store decision)
