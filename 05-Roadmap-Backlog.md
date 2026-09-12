# Project Roadmap

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | v1.1 — eleven phases, application first then agents. Phase 1 nearly done |
| **Updated** | 2026-09-12 |

---

## 1. The approach

**Make the whole application work end to end first, then make it intelligent.** Phases 1–4 build a
product a person can use by hand. Phase 5 adds the first LLM, called straight from the API. Phases
6–11 turn that into the agentic system: retrieval, tools, agents, the extension, and the evals that
prove it behaves.

The order is deliberate. An agent writing into a half-built app cannot be judged, and a broken
pipeline is far harder to debug with an LLM in the middle of it — so the plumbing is finished before
anything starts reasoning.

| Phase | Delivers | State |
|---|---|---|
| [1](#2-phase-1--authentication--profile) | Sign in, and the profile everything hangs off | 🚧 nearly done |
| [2](#3-phase-2--resume-generation--download) | A resume built from that profile, downloadable | 🚧 backend done, no UI |
| [3](#4-phase-3--job-scraping-search--shortlist) | Real jobs in the system, searchable and shortlistable | ⬜ API only |
| [4](#5-phase-4--applications--settings) | Tracking what you applied to, and the preferences driving it | ⬜ API only |
| [5](#6-phase-5--llm-integration--resume-rectification) | A resume rectified against a specific job | ⬜ not started |
| [6](#7-phase-6--rag--retrieval) | Retrieval over your own resume, with the split vector store | ⬜ not started |
| [7](#8-phase-7--mcp-tool-servers) | The tool servers agents reach the world through | ⬜ not started |
| [8](#9-phase-8--agents--orchestration) | LangGraph agents under a supervisor, with approval interrupts | ⬜ not started |
| [9](#10-phase-9--application-agent--chrome-extension) | Form autofill in your own browser session | ⬜ not started |
| [10](#11-phase-10--eval-guardrails--observability) | Ragas faithfulness, guardrail tests, tracing | ⬜ not started |
| [11](#12-phase-11--daily-use--polish) | What only real daily use reveals | ⬜ not started |

**How to read a phase.** Each is split into **API**, **UI** and, where relevant, infrastructure and
guardrail tasks — so you can see at a glance that a phase's backend is done while its screens are
not, which is the usual state here.

| Mark | Meaning |
|---|---|
| ✅ | Built and manually exercised |
| 🟡 | Partial — some artefacts exist, story incomplete |
| ⬜ | Not started |
| ⛔ | Superseded — will not be built as written |

A checked **UI** box means the screen is built; it does **not** mean it talks to the API. Where a
screen exists but still reads a JSON fixture, the wiring is listed as its own unchecked task.

Each task appears once, under the phase that delivers it. The old epic grouping and its story IDs
are retired — nothing outside this document referenced them.

---

## 2. Phase 1 — Authentication & Profile
🚧 **nearly done.** The account you sign in as, and the resume material hanging off it. Everything
else in the product is keyed by `userId`, so this comes first.

**API**
- ✅ `accounts` collection: argon2 password hashes, unique index on email
- ✅ Signup and login both issue a JWT; signup signs you straight in, no second call
- ✅ `account` module: signup, login, read one account, partial update
- ✅ Profile split into five collections keyed by `userId` — `profile`,
  `work_experience`, `education`, `skills`, `certifications`
- ⬜ **Server-side enforcement.** Endpoints take `userId` from the URL and never check
  it against the token, so any signed-in account can read or write another's profile
- ⬜ Retire the duplicate `user` module, or fold it into `account`
- ⬜ Token refresh and expiry handling beyond the 60-minute TTL

**UI**
- ✅ Login and Signup screens, wired to `/api/account` for real
- ✅ Session in `sessionStorage`, mirrored into Redux, restored on refresh
- ✅ Route guard: every dashboard page redirects to `/login` without a session
- ✅ Bearer token attached to every API call; a 401 clears the session
- ✅ My Details screen built, with Formik/Yup validation on every field
- ⬜ **Wire My Details to the profile API.** Today only `role` persists (via the
  account endpoint); name, headline, phone, location, summary, links, experience, education,
  skills and certifications all still come from `profile.json`

---

## 3. Phase 2 — Resume generation & download
🚧 **backend done, no UI.** Turn the profile into a document you can send. No LLM in this phase —
it is templating, not intelligence.

**API**
- ✅ `templates` collection: `.tex` source, token list, preview path, archive flag
- ✅ Upload endpoint with token validation, rejecting templates nothing can fill
- ✅ Style inference from the `.tex` itself (contact, skills, experience, columns)
- ✅ Render a profile into a template: `GET /template/render/{templateId}/{userId}`
- ✅ `template` module: upload, list, read source, update, preview image
- 🟡 Jinja2 wrapper over `base_resume.tex` (custom `\VAR{}`/`\BLOCK{}`
  delimiters). *Partial — validated by a throwaway script, not by anything in the codebase*
- ⬜ Download the generated `.tex`
- ⬜ PDF compilation and download

**UI**
- ✅ Resume Preview screen built: Preview / Diff / Source tabs
- ⬜ Point the Resume Preview screen at a real render instead of `resume.json`
- ⬜ Template picker in the dashboard

**Verification**
- ⬜ **Prove a rendered `.tex` compiles under a TeX engine.** No output of this
  pipeline has ever been through one, so its LaTeX validity is unconfirmed

**PDF compilation was promoted** from the v1 stretch list: "generate and download" is hollow if the output
is a `.tex` the reader cannot open. It needs a TeX engine and an amendment to invariant 5 / FR-4.4.

---

## 4. Phase 3 — Job scraping, search & shortlist
⬜ **API only.** Get real jobs into the system so the screens that already exist have something to
work on.

**API**
- ✅ `job` module: create with dedup-hash check, list by status, shortlist toggle
- ⬜ Indeed MCP connector
- ⬜ Google CSE / SerpAPI search
- ⬜ Dedup logic on content hash
- ⬜ Adapt the `linkedin-hiring-scraper` skill as a tool
- ⬜ Naukri and company career-page sources
- ⬜ Scheduled daily run *(needs Redis + Celery, below)*

**UI**
- ✅ Job Search screen built (multi-field search + facets)
- ✅ Shortlist / Match Review screen built
- ✅ Job Details screen built
- ⬜ Wire all three screens off `search.json` and onto the job API

**Infrastructure**
- ⬜ Redis + Celery for scheduling

**Sequence that matters:** one source working end to end beats four half-built connectors. The
Indeed connector plus content-hash dedup is the smallest thing that makes the three screens real.

---

## 5. Phase 4 — Applications & Settings
⬜ **API only.** The tracking half of the product, plus the preferences that will later drive
discovery.

**API**
- ✅ `application` module: stage, record fill, status transitions, answer bank
- ⬜ **Rebuild a preferences store for Settings.** `profile.preferences` was removed
  on 2026-09-11, so target roles, locations, company preference and discovery schedule have
  nowhere to live
- ⬜ Follow-up draft generation on an interval
- ⬜ Google Sheet sync

**UI**
- ✅ Staged Applications screen built
- ✅ Pipeline board built
- ✅ "Pending your review" banner built
- ✅ Settings screen built
- ⬜ Wire all three screens onto the application API and real counts
- ⬜ Wire the Settings screen onto that store, once it exists

**The preferences store is new work, not a wiring job** — that screen has no backend at all today.

---

## 6. Phase 5 — LLM integration & resume rectification
⬜ **not started.** The first intelligence in the product, called directly from the API. Still no
agents and no orchestration — deliberately, so a wrong answer stays debuggable.

**API**
- ✅ `match` module: write score and keywords, record the user's selection
- ✅ `resume` module: versioned `.tex` + selection set, rejects unselected keywords
- ⬜ Structured keyword extraction from a JD
- ⬜ Present / Missing keyword diff against the profile
- ⬜ Risk-flag detection (seniority mismatch and similar)
- ⬜ Embed the JD, `$vectorSearch`, compute a match score *(needs Atlas, below)*
- ⬜ Incorporate **only** the keywords the user ticked
- ⬜ Version each `.tex` per job id

**UI**
- ✅ Keyword Selection screen built, starting with nothing checked (FR-2.5)
- ⬜ Wire it onto real match data instead of `matches.json`

**Infrastructure**
- ⬜ Pick and validate a local LLM; confirm tool-calling reliability
- 🟡 Atlas free tier + `$vectorSearch` index. *Partial — local store done, Atlas
  not started*

**Guardrail**
- ⬜ No-fabrication test cases

**The guardrail is the point of this phase.** Tailoring from ticked keywords only, and the tests
proving it, are what make "no fabrication" real rather than aspirational — and neither can be
claimed while the API has no test suite.

---

## 7. Phase 6 — RAG & retrieval
⬜ **not started.** Tailoring and scoring should work against what your resume actually says, not
against the whole document stuffed into a prompt. This is the retrieval layer that makes that true.

**API**
- ⬜ RAG second hop: `resume_chunk_text` and the local text fetch by `chunk_id`
  *(this existed and was removed on 2026-09-11; it comes back here)*
- ⬜ Chunk the profile into retrievable units, section by section
- ⬜ Re-index on profile edit, so retrieval never serves stale text

**AI tier**
- ⬜ Embed chunks and store vectors in Atlas — **ids and vectors only, never prose**
- ⬜ Two-stage retrieval: `$vectorSearch` top ~50 → fetch text from `server` → rerank
  → top ~5

**Infrastructure**
- ⬜ Atlas free tier + `$vectorSearch` index, dimension matching the embedding model

**The split store is the point.** Atlas holds vectors and `chunk_id`s; the text stays in local
MongoDB. That is why retrieval needs two hops, and why the chunk store is a prerequisite rather
than an optimisation.

---

## 8. Phase 7 — MCP tool servers
⬜ **not started.** The agents in Phase 8 reach the outside world only through these, so they come
first.

**AI tier**
- ⬜ `jobpilot_api` — the one way agents read and write structural data, over HTTP
- ⬜ `latex` — render a tailored `.tex` from a template and a profile
- ⬜ `job_search` — Google CSE / SerpAPI behind one tool interface
- ⬜ `indeed` and `linkedin` source servers
- ⬜ `browser` — Playwright, for discovery only
- ⛔ MongoDB MCP Server. *Superseded: agents go through `jobpilot_api` over HTTP
  instead, so there is one validation boundary and no DB credentials in the agent process*

---

## 9. Phase 8 — Agents & orchestration
⬜ **not started.** Phases 3 and 5 do discovery and matching as plain endpoints. This phase turns
them into agents under a supervisor that can pause for a human.

**AI tier**
- ⬜ Job Discovery agent — scheduled, multi-source, dedup-aware
- ⬜ JD Match & Score agent — extraction, diff, scoring over RAG
- ⬜ Resume Tailor agent — selected keywords only, rendering through the `latex` server
- ⬜ Tracking & Follow-up agent — status transitions and interval drafts
- ⬜ LangGraph supervisor wiring all agents with shared state
- ⬜ **Human-approval interrupts** at keyword selection and application review
- ⬜ Retry and error handling per agent step

**UI**
- ⬜ Surface an interrupt in the dashboard — the approval gate needs somewhere to happen

**The approval interrupts are not a feature, they are the guardrail.** The supervisor must be unable to run past those
two interrupts; see the Design Principles in the README.

---

## 10. Phase 9 — Application agent & Chrome extension
⬜ **not started.** The last manual step: filling the form. Fills, never submits.

**Extension**
- ⬜ Scaffold (Manifest V3, content script, background worker, popup)
- ⬜ Field detection by label / ARIA / placeholder heuristics
- ⬜ LLM fallback for ambiguous fields
- ⬜ Highlight every filled field for review
- ⬜ Manual resume-attach flow
- ⬜ Workday / Greenhouse / Lever field patterns
- ⬜ LinkedIn Easy Apply

**API**
- ⬜ Serve job context and the Q&A answer bank to the extension
- ⬜ Application agent coordinating the fill from the `ai` tier

**Runs in your real browser session**, not an automated one — more reliable against ATS platforms,
and it keeps you in the loop by construction.

---

## 11. Phase 10 — Eval, guardrails & observability
⬜ **not started.** The phase that turns "it seems to work" into something measured. Everything
above is unprovable until this exists.

**Eval**
- ⬜ Ragas suite: **faithfulness** (the automated no-fabrication check), context
  precision and recall
- ⬜ Eval datasets built from real JDs and real profile content
- ⬜ A **local** judge model, so evaluation does not leak what generation protects

**Guardrails**
- ⬜ No-fabrication test cases
- ⬜ No-auto-submit test cases
- ⬜ The API test suite *(also in §13 — it blocks every phase, not just this one)*

**Observability**
- ⬜ Langfuse or Phoenix, self-hosted

---

## 12. Phase 11 — Daily use & polish
⬜ **not started.** The phase that only real usage can write.

- ⬜ Bug fixes from actually running the daily workflow
- ⬜ Q&A answer-bank refinement from real applications
- ⬜ Performance and cost tuning on the local models
- ⬜ Cover letter generation *(stretch)*

---

## 13. Cross-cutting — true of every phase

- ✅ FastAPI app shell: thin `main.py`, localhost bind, CORS for web + extension
- ✅ Beanie documents for every local collection, `ObjectId` keys
- ✅ React frontend, built in v1 instead of Streamlit/Gradio *(closed — see
  deviation 1)*
- ⬜ **Test suite for the API and its guardrails.** Removed on request; blocks the §15
  Definition of Done in every phase above
- ⬜ CI/CD via GitHub Actions (lint and test on push)

**The test suite and server-side token enforcement are the two that should not wait.** Neither
blocks building the next feature, and both should close before this is used against real job
applications.

---

## 14. Implementation status

The dashboard UI was built ahead of the backend. `server/` is now built — ten modules, 54 endpoints,
14 collections — and the auth screens run against it end to end. Every other screen still renders
from a JSON fixture in `app/web/src/data/`, so apart from sign-in **no story meets the §10
Definition of Done** (the §15 test-case requirement is unmet everywhere; `server/` has no tests).

`ai/` and the Chrome extension do not exist yet, so nothing agentic runs.

| Built | Backed by |
|---|---|
| Pipeline board · Shortlist · Staged Applications · Job Search · Job Details · Settings | `board.json` `search.json` `applications.json` `settings.json` |
| Keyword Selection — starts with nothing checked, per FR-2.5 | `matches.json` |
| Resume Preview — Preview / Diff / Source tabs, `.tex` download | `resume.json` + `templates/base_resume.tex` |
| **Login · Signup · sign-out · route guard** | **live — `POST /api/account/{signup,login}`, JWT in `sessionStorage`, mirrored into Redux** |
| My Details — identity, experience, education, skills, certifications | `profile.json`; only **Role** persists, via `PATCH /api/account/updateAccount/{id}` |

**Five deviations from this document, recorded deliberately:**

1. **Next.js, not Streamlit/Gradio.** The original plan named Streamlit or Gradio and
   deferred a React frontend to v2. The dashboard was built directly in Next.js + Tailwind, matching
   the stack in `CLAUDE.md` and doc 03. That path is therefore **closed, not deferred**, and the
   Streamlit/Gradio path was never taken.
2. **`templates/base_resume.tex` exists and renders, but nothing in `ai/` drives it.** The Jinja2
   render (custom `\VAR{}`/`\BLOCK{}` delimiters) was validated with a throwaway script, not by
   `ai/mcp_servers/latex/`. The Jinja2 wrapper stays partial, and the template has **never been compiled by a
   TeX engine** — its LaTeX validity is unverified.
3. **Authentication was built**, which PRD §4, SRS §42 and `.claude/rules/server-api.md` all rule out
   on single-user grounds. As of 2026-09-11 the screens are no longer interface-only: accounts are
   stored with argon2 hashes, login and signup both issue a JWT, and every dashboard route redirects
   to `/login` without one. **Those three documents are now wrong and need amending** — the decision
   went the other way. Reopened as in scope.
4. **`profile.preferences` and `resume_chunk_text` were removed** (2026-09-11) to keep the profile
   module focused on resume material. The Settings screen therefore has no backend, and the RAG
   second hop no longer exists — it is rebuilt in Phase 6. Doc 06 and doc 03
   still describe both.
5. **The profile is five collections, not one embedded document.** `profile`, `work_experience`,
   `education`, `skills` and `certifications`, each keyed by `userId` = `accounts._id`. Doc 06
   describes the earlier single-document shape.

**Note:** MVP (Phases 2–4, manual apply) is realistically achievable in **2–3 weeks** if you want to
start using it before the full system is built. The original estimate assumed single-user scope
removed all auth overhead; that assumption no longer holds — see deviation 3.

---

---

## 15. Definition of Done (per story, general)

- Functionality works end-to-end against real (or realistic test) data — and against the local
  LLM from Phase 5 onward, where one is involved
- No hard-coded secrets; config via environment variables
- Guardrail-relevant stories (fabrication, auto-submit) have explicit test cases proving the guardrail holds
- Manually exercised by the user (Swarup) at least once in the actual daily workflow before marked Done

---

---

## 16. Stretch — candidates beyond Phase 11

- ~~PDF compilation of tailored `.tex` resumes~~ — **promoted into Phase 2.** "Generate and
  download" is hollow without it; still needs a TeX engine and an amendment to invariant 5 / FR-4.4
- Cover letter generation — carried in Phase 11
- LinkedIn Easy Apply full support — carried in Phase 9 rather than dropped
- A2A-based Application Agent as an independently scalable service
- Multi-device sync (if ever needed — would require revisiting the single-user Atlas-only vector store decision)
