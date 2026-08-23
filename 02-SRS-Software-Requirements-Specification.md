# Software Requirements Specification (SRS)

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | Draft v1.0 |

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for JobPilot, a single-user agentic AI system for job discovery, resume tailoring, and application management.

### 1.2 Definitions & Acronyms

| Term | Meaning |
|---|---|
| JD | Job Description |
| ATS | Applicant Tracking System (e.g., Workday, Greenhouse, Lever) |
| MCP | Model Context Protocol — tool-access layer for agents |
| A2A | Agent2Agent protocol — optional inter-agent service communication |
| LLM | Large Language Model |
| Present/Missing list | Keywords found in the JD that are/aren't already in the resume |
| `.tex` | LaTeX source file (resume output format, pre-PDF) |

### 1.3 Scope
Covers the full agent system: Job Discovery, JD Match/Score, Resume Tailor, Application (Chrome extension), Tracking & Follow-up, and the Orchestrator, plus the local dashboard and data layer.

---

## 2. Overall Description

### 2.1 Product Perspective
Standalone, locally-run system. No dependency on Claude or any hosted commercial LLM at runtime — uses self-hosted local LLMs (Ollama/vLLM). MongoDB is split between local (structural data) and Atlas free tier (vector search data). Agents are orchestrated via LangGraph and access tools via MCP.

### 2.2 User Characteristics
Single technical user (software engineer) — no requirement for simplified/non-technical UX, but the dashboard should still minimize friction for daily use.

### 2.3 Constraints
- Single-user only — no auth/RBAC/multi-tenant schema required
- Local LLM function-calling reliability must be validated per model before use in production agents
- macOS host: `mongot` (MongoDB's local vector search engine) has no native macOS build — Atlas free tier used for vector data instead
- Job board ToS prohibit automated form submission — system must keep a human-approval gate before any application is submitted

### 2.4 Assumptions
- User has adequate local compute (GPU/CPU) to run a 7B–32B+ class local LLM at usable latency
- User's Chrome browser remains the environment for the Application Agent's autofill step
- User will periodically review/update the Q&A answer bank used for screening questions

---

## 3. Functional Requirements

### FR-1 — Job Discovery
- **FR-1.1** The system shall query configured sources (Google/SerpAPI, Indeed MCP, LinkedIn, Naukri) on a scheduled interval (default: daily).
- **FR-1.2** The system shall normalize each result into a common schema: title, company, location, JD text, source URL, posted date.
- **FR-1.3** The system shall deduplicate listings using a content hash before storing.
- **FR-1.4** The system shall respect `robots.txt` and rate limits for any scraped source; official APIs/MCP connectors shall be preferred where available.

### FR-2 — JD Keyword Extraction & Match Scoring
- **FR-2.1** The system shall extract technical keywords/skills from a given JD using structured LLM extraction.
- **FR-2.2** The system shall compute a semantic match score between the JD and the user's resume/profile using vector similarity.
- **FR-2.3** The system shall produce a **Present** list (keywords already in the resume) and a **Missing** list (keywords in the JD but not the resume).
- **FR-2.4** The system shall flag risk cases (e.g., seniority mismatch) distinctly from ordinary missing keywords.
- **FR-2.5** The system shall NOT auto-incorporate any missing keyword into the resume without explicit user selection.

### FR-3 — Interactive Keyword Selection
- **FR-3.1** The system shall present the Present/Missing lists to the user for review.
- **FR-3.2** The system shall allow the user to select any subset of Missing keywords to incorporate.
- **FR-3.3** The system shall pass only the user's selections to the Resume Tailor Agent as tailoring instructions.

### FR-4 — Resume Tailoring
- **FR-4.1** The system shall generate a tailored `.tex` resume file based on the existing `base_resume.tex` template and custom LaTeX commands.
- **FR-4.2** The system shall incorporate only user-selected keywords (FR-3.2) — no unselected additions.
- **FR-4.3** The system shall version each tailored `.tex` file per job ID.
- **FR-4.4** The system shall NOT compile the `.tex` to PDF in v1 — output is source only.

### FR-5 — Application Autofill (Chrome Extension)
- **FR-5.1** The extension shall detect form fields on the current job application page (inputs, selects, textareas).
- **FR-5.2** The extension shall match detected fields to known answers (profile data + Q&A bank) using label/ARIA/placeholder heuristics, with LLM fallback for ambiguous fields.
- **FR-5.3** The extension shall fill matched fields automatically but shall NOT submit the form.
- **FR-5.4** The extension shall visually indicate which fields were auto-filled so the user can review before submitting.
- **FR-5.5** The extension shall surface the correct tailored resume file's location for manual attach (file inputs cannot be set programmatically).

### FR-6 — Tracking & Follow-up
- **FR-6.1** The system shall maintain application status across a defined pipeline (Applied → Viewed → Interview → Offer/Rejected).
- **FR-6.2** The system shall generate follow-up email drafts at configurable intervals per application.
- **FR-6.3** The system shall sync status changes to the user's existing Google Sheet tracker.

### FR-7 — Orchestration
- **FR-7.1** The system shall coordinate agent execution via a LangGraph state machine.
- **FR-7.2** The system shall persist shared state (profile, job queue, in-flight applications) across agent steps.
- **FR-7.3** The system shall pause execution at defined human-approval checkpoints (keyword selection, application review) and resume only after user input.
- **FR-7.4** The system shall retry failed agent steps with bounded backoff before surfacing an error to the user.

### FR-8 — Data Access
- **FR-8.1** Agents shall access MongoDB (local and Atlas) exclusively through the MongoDB MCP Server, not direct hand-rolled clients per agent.
- **FR-8.2** Vector-search queries shall be routed to the Atlas-hosted collections; structural CRUD shall be routed to the local instance.

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | Job-posted → tailored-`.tex`-ready end-to-end under 5 minutes for a single job |
| NFR-2 | Reliability | Local LLM tool-calling accuracy validated per model before use in Orchestrator/Resume Tailor Agent; JSON-mode/grammar-constrained decoding used as fallback for structured outputs |
| NFR-3 | Privacy | No resume, JD, or PII data sent to third-party hosted LLM APIs; all inference local |
| NFR-4 | Security | Local dashboard access restricted to localhost/LAN; no public internet exposure by default |
| NFR-5 | Portability | System must run on macOS (primary dev environment) without requiring `mongot`/Docker for the structural DB path |
| NFR-6 | Maintainability | Each agent implemented as an independently testable LangGraph node with clear input/output contracts |
| NFR-7 | Compliance | No automated form submission without explicit human review, in line with target ATS platforms' Terms of Service |
| NFR-8 | Auditability | Every tailored resume's incorporated keywords traceable back to explicit user selections (no silent additions) |

---

## 5. External Interface Requirements

| Interface | Direction | Description |
|---|---|---|
| Local LLM API (Ollama/vLLM) | Agent → LLM | OpenAI-compatible `/v1/chat/completions` endpoint |
| MongoDB MCP Server | Agent → DB | Structured + vector data access |
| Indeed MCP Connector | Job Discovery Agent → Indeed | Official job listing retrieval |
| Chrome Extension ↔ Local Backend | Extension → FastAPI | HTTP (localhost) — job context, answer payloads |
| Google Sheets | Tracking Agent → Sheet | Status sync (existing tracker) |
| LaTeX Template | Resume Tailor Agent → Filesystem | Reads `base_resume.tex`, writes tailored `.tex` per job |

---

## 6. Data Requirements (summary — full schema in Architecture doc)

- `profile`, `jobs`, `matches`, `applications`, `events` — local MongoDB
- `jobs.jd_embedding`, `profile.resume_chunks` — MongoDB Atlas (vector-indexed)
- `job_id` is the join key linking local and Atlas records

---

## 7. System Constraints Recap

- Single-user, no multi-tenant design
- Local-LLM-only inference — no Claude/OpenAI/cloud LLM at runtime
- Human-approval gate mandatory before any application submission
- `.tex`-only resume output in v1 (no PDF compile step yet)
