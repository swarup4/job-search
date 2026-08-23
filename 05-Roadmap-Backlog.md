# Project Roadmap & Backlog

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | Draft v1.0 |

---

## 1. Roadmap (Phased, ~8–10 weeks, single-user scope)

### Phase 0 — Foundation (Week 1)
- Define target role/location profile schema
- Set up local MongoDB (structural data) + MongoDB Atlas free tier (vector-search collections) + Redis
- Create `$vectorSearch` index on Atlas `jobs.jd_embedding`
- Set up MongoDB MCP Server
- Stand up LangGraph project skeleton with a no-op orchestrator
- Pick and validate local LLM (Ollama for dev) — confirm tool-calling reliability

### Phase 1 — Job Discovery Agent (Weeks 2–3)
- Integrate Indeed MCP + SerpAPI/Google CSE
- Adapt `linkedin-hiring-scraper` skill into an agent tool
- Dedup + normalize + store pipeline into local MongoDB
- Scheduled daily run via Celery beat

### Phase 2 — JD Match & Resume Tailor Agents (Weeks 3–4)
- JD keyword extraction + Present/Missing diff against resume
- Keyword-selection UI step
- Jinja2-based `.tex` generator wrapping `resume-maker` template
- "No fabrication" guardrail — only selected keywords incorporated
- Scope: `.tex` output only, no PDF compile yet

### Phase 3 — Application Agent, Chrome Extension (Weeks 5–6)
- Build extension (Manifest V3): content script, background worker, popup
- Field-matching heuristics for 2–3 ATS platforms (Workday, Greenhouse, Lever)
- Local FastAPI backend serving job context/Q&A answers
- Manual resume-attach flow (file path copy)

### Phase 4 — Tracking Dashboard (Weeks 6–7)
- Streamlit/Gradio dashboard: pipeline board, shortlist review, staged applications
- Google Sheet sync
- Follow-up draft generation on interval triggers

### Phase 5 — Multi-agent Orchestration (Weeks 7–8)
- Wire all agents into LangGraph supervisor with shared state
- Implement human-approval interrupts (keyword selection, application review)
- Retry/error handling for failed agent steps

### Phase 6 — Eval & Guardrails (Weeks 8–9)
- Eval suite (Langfuse/Phoenix): match-score accuracy, resume-tailor faithfulness, form-fill accuracy
- Guardrail test cases: no-fabrication, no-auto-submit

### Phase 7 — Polish & Daily Use (Weeks 9–10)
- Bug fixes from real daily usage
- Q&A answer bank refinement
- Optional: PDF compilation step, cover letter generation (stretch goals — see Backlog)

**Note:** given single-user scope removes auth/multi-tenant overhead, MVP (Phases 0–2, manual apply) is realistically achievable in **2–3 weeks** if you want to start using it before the full system is built.

---

## 2. Product Backlog (Epics → Stories)

### Epic 1: Infrastructure & Data Layer
| ID | Story | Priority |
|---|---|---|
| INFRA-1 | Set up local MongoDB + Atlas free tier + `$vectorSearch` index | Must |
| INFRA-2 | Set up MongoDB MCP Server | Must |
| INFRA-3 | Set up Redis + Celery for scheduling | Must |
| INFRA-4 | Validate local LLM tool-calling reliability (Ollama, target model) | Must |
| INFRA-5 | Set up Langfuse/Phoenix for eval/observability | Should |
| INFRA-6 | CI/CD via GitHub Actions (lint/test on push) | Could |

### Epic 2: Job Discovery
| ID | Story | Priority |
|---|---|---|
| DISC-1 | Integrate Indeed MCP connector | Must |
| DISC-2 | Integrate Google CSE/SerpAPI search | Must |
| DISC-3 | Adapt `linkedin-hiring-scraper` skill as agent tool | Should |
| DISC-4 | Dedup logic (content hash) | Must |
| DISC-5 | Scheduled daily run (Celery beat) | Must |
| DISC-6 | Naukri / company career page sources | Could |

### Epic 3: JD Match & Keyword Selection
| ID | Story | Priority |
|---|---|---|
| MATCH-1 | LLM structured keyword extraction from JD | Must |
| MATCH-2 | Embed JD → Atlas `$vectorSearch`, compute match score | Must |
| MATCH-3 | Present/Missing keyword diff logic | Must |
| MATCH-4 | Risk-flag detection (seniority mismatch, etc.) | Should |
| MATCH-5 | Keyword Selection UI (checkbox screen) | Must |

### Epic 4: Resume Tailoring
| ID | Story | Priority |
|---|---|---|
| TAILOR-1 | Jinja2 template wrapper over `base_resume.tex` (custom delimiters) | Must |
| TAILOR-2 | Incorporate only user-selected keywords | Must |
| TAILOR-3 | Version `.tex` files per job ID | Must |
| TAILOR-4 | Resume Tailor Preview screen (diff view) | Should |
| TAILOR-5 | (Stretch) PDF compilation step | Won't (v1) |
| TAILOR-6 | (Stretch) Cover letter generation | Won't (v1) |

### Epic 5: Application Autofill (Chrome Extension)
| ID | Story | Priority |
|---|---|---|
| APPLY-1 | Extension scaffold (Manifest V3, content script, popup) | Must |
| APPLY-2 | Field-detection heuristics (label/ARIA/placeholder matching) | Must |
| APPLY-3 | LLM fallback for ambiguous field matching | Should |
| APPLY-4 | Local FastAPI backend (job context + Q&A bank) | Must |
| APPLY-5 | Highlight filled fields for review | Must |
| APPLY-6 | Manual resume-attach flow (copy file path) | Must |
| APPLY-7 | Workday/Greenhouse/Lever field-pattern support | Should |
| APPLY-8 | LinkedIn Easy Apply support | Could |

### Epic 6: Tracking & Dashboard
| ID | Story | Priority |
|---|---|---|
| TRACK-1 | Pipeline board (Streamlit/Gradio) | Must |
| TRACK-2 | Job Shortlist / Match Review screen | Must |
| TRACK-3 | Staged Applications screen | Must |
| TRACK-4 | "Pending your review" banner (approval-gate surface) | Must |
| TRACK-5 | Follow-up draft generation on interval | Should |
| TRACK-6 | Google Sheet sync | Should |
| TRACK-7 | (Stretch) React frontend upgrade | Won't (v1) |

### Epic 7: Orchestration & Guardrails
| ID | Story | Priority |
|---|---|---|
| ORCH-1 | LangGraph supervisor wiring all agents | Must |
| ORCH-2 | Human-approval interrupts (keyword selection, application review) | Must |
| ORCH-3 | Retry/error handling per agent step | Must |
| ORCH-4 | No-fabrication guardrail test cases | Must |
| ORCH-5 | No-auto-submit guardrail test cases | Must |

---

## 3. Sprint Breakdown (2-week sprints, ~5 sprints)

| Sprint | Focus | Backlog Items |
|---|---|---|
| Sprint 1 (Wks 1–2) | Foundation + Discovery start | INFRA-1–4, DISC-1–5 |
| Sprint 2 (Wks 3–4) | Match + Tailor | MATCH-1–5, TAILOR-1–4 |
| Sprint 3 (Wks 5–6) | Application Extension | APPLY-1–7 |
| Sprint 4 (Wks 7–8) | Dashboard + Orchestration | TRACK-1–6, ORCH-1–3 |
| Sprint 5 (Wks 9–10) | Guardrails + Polish | ORCH-4–5, INFRA-5, real-usage bug fixes |

---

## 4. Definition of Done (per story, general)

- Functionality works end-to-end against local LLM + real (or realistic test) data
- No hard-coded secrets; config via environment variables
- Guardrail-relevant stories (fabrication, auto-submit) have explicit test cases proving the guardrail holds
- Manually exercised by the user (Swarup) at least once in the actual daily workflow before marked Done

---

## 5. Stretch / Backlog (Won't-have in v1, candidates for v2)

- PDF compilation of tailored `.tex` resumes
- Cover letter generation
- LinkedIn Easy Apply full support
- React frontend upgrade from Streamlit/Gradio
- A2A-based Application Agent as an independently scalable service
- Multi-device sync (if ever needed — would require revisiting the single-user Atlas-only vector store decision)
