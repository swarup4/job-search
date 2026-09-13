# Project Roadmap

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | v1.4 — eleven phases, application first then agents. Phase 1 done; audited 2026-09-13 |
| **Updated** | 2026-09-13 |

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
| [1](#2-phase-1--authentication--profile) | Sign in, and the profile everything hangs off | ✅ done |
| [2](#3-phase-2--resume-generation--download) | A resume built from that profile, downloadable | 🚧 backend done, no UI |
| [3](#4-phase-3--job-scraping-search--shortlist) | Real jobs in the system, searchable and shortlistable | ⬜ API only, no sources |
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

Each task appears once, under the phase that delivers it, and carries an id: `P1-06` is the sixth
task of Phase 1, counting through that phase's **API**, **UI** and other sections in order.
Cross-cutting tasks (§13) use `CC-`. The id is for referring to a task in a commit message or a
conversation — nothing outside this document generates or validates them.

**Add new tasks at the end of their section** rather than inserting them mid-list. Numbering is
positional, so an insert renumbers every task below it and any id you wrote down elsewhere goes
stale. The ids are intentionally coarse for the same reason: a phase, and a position in it.

---

## 2. Phase 1 — Authentication & Profile
✅ **done.** The account you sign in as, and the resume material hanging off it. Everything else in
the product is keyed by `userId`, so this comes first.

**API**
- ✅ `P1-01` `accounts` collection: argon2 password hashes, unique index on email
- ✅ `P1-02` Signup and login both issue a JWT; signup signs you straight in, no second call.
  Signup takes name, email and password and nothing else — role and picture are set
  later from My Details
- ✅ `P1-03` `account` module: signup, login, refresh, read one account, partial update
- ✅ `P1-04` Profile split into five collections keyed by `userId` — `profile`,
  `work_experience`, `education`, `skills`, `certifications`
- ✅ `P1-05` Name and email live on `accounts` only. The `profile` collection held a second
  copy of both; it now starts at `headline`, and the renderer reads the two off the
  account. Saving them is `PATCH /account/updateAccount`, same as `role`
- ✅ `P1-06` **Server-side enforcement.** Every endpoint outside signup/login/refresh requires a
  bearer token, and **no URL carries a user id any more** — one `verify_token` dependency
  reads it from the token and hands it to the route. Reading another user's data is not
  refused, it is unreachable: there is nowhere to name them
- ✅ `P1-07` **Every collection is keyed by `userId`**, not just the profile ones: `jobs`,
  `matches`, `resumes`, `applications`, `answer_bank` and `events` each carry the owning
  account, and every query filters on it. Another user's id reads as 404, never 403 —
  the caller has no business learning the row exists
- ✅ `P1-08` Dedup is per user. `jobs.dedup_hash` was globally unique, so the second person to
  find a posting would have been handed the first person's row; it is now unique per
  `(userId, dedup_hash)`. Same for `answer_bank.key`
- ✅ `P1-09` Retired the duplicate `user` module. It was dead weight and a liability — plaintext
  passwords, its own signup, and a `GET /api/user` that returned every row. The `users`
  collection is left in Mongo, simply no longer mapped
- ✅ `P1-10` Dropped `GET /api/account`, which listed every account to any caller. Nothing used it
- ✅ `P1-11` Token refresh and expiry. Access token keeps its 60-minute TTL and gains `typ`;
  a 30-day refresh token is spent and replaced on each `POST /account/refresh`, so a
  session in daily use never signs in again and an idle one still expires

**UI**
- ✅ `P1-12` Login and Signup screens, wired to `/api/account` for real
- ✅ `P1-13` Session in `sessionStorage`, mirrored into Redux, restored on refresh
- ✅ `P1-14` Route guard: every dashboard page redirects to `/login` without a session
- ✅ `P1-15` Bearer token attached to every API call; a 401 clears the session
- ✅ `P1-16` A 401 refreshes once and replays the call before giving up on the session —
  one refresh shared across the several calls a screen fires together
- ✅ `P1-17` My Details screen built, with Formik/Yup validation on every field
- ✅ `P1-18` **My Details is wired to the profile API.** The screen loads from
  `getAccount` plus the five profile endpoints on mount, and one Save persists all of it:
  name and role to `PATCH /account/updateAccount`, the rest to the profile endpoints,
  creating the profile row on first save. Entries added in the browser pick up their
  server ids from the response, so a second save updates instead of duplicating. Email is
  read-only — it is the login key. Only the retrieval panel still reads `profile.json`,
  and that is Phase 6 work

---

## 3. Phase 2 — Resume generation & download
🚧 **backend done, no UI.** Turn the profile into a document you can send. No LLM in this phase —
it is templating, not intelligence.

**API**
- ✅ `P2-01` `templates` collection: `.tex` source, token list, preview path, archive flag
- ✅ `P2-02` Upload endpoint with token validation, rejecting templates nothing can fill
- ✅ `P2-03` Style inference from the `.tex` itself (contact, skills, experience, columns)
- ✅ `P2-04` Render the signed-in user's profile into a template: `GET /template/render/{templateId}`
- ✅ `P2-05` `template` module: upload, list, read source, update, preview image
- ⛔ `P2-06` Jinja2 wrapper over `base_resume.tex` (custom `\VAR{}`/`\BLOCK{}`
  delimiters). *Superseded: the `template` module renders `{{TOKEN}}` placeholders out of
  uploaded `.tex` files instead. There is no `jinja2` dependency, `base_resume.tex` carries
  no `\VAR{}` or `\BLOCK{}` markers — only comments describing them — and nothing reads it*
- ⬜ `P2-07` Download the generated `.tex`
- ⬜ `P2-08` PDF compilation and download

**UI**
- ✅ `P2-09` Resume Preview screen built: Preview / Diff / Source tabs
- ⬜ `P2-10` Point the Resume Preview screen at a real render instead of `resume.json`
- ⬜ `P2-11` Template picker in the dashboard

**Verification**
- ⬜ `P2-12` **Prove a rendered `.tex` compiles under a TeX engine.** No output of this
  pipeline has ever been through one, so its LaTeX validity is unconfirmed

**PDF compilation was promoted** from the v1 stretch list: "generate and download" is hollow if the output
is a `.tex` the reader cannot open. It needs a TeX engine and an amendment to invariant 5 / FR-4.4.

---

## 4. Phase 3 — Job scraping, search & shortlist
⬜ **API only.** Get real jobs into the system so the screens that already exist have something to
work on.

**API**
- ✅ `P3-01` `job` module: create with dedup-hash check, list by status, shortlist toggle
- ⬜ `P3-02` Indeed MCP connector
- ⬜ `P3-03` Google CSE / SerpAPI search
- ✅ `P3-04` Dedup logic on content hash: sha256 over title, company, location and
  `jd_text`, unique per `(userId, dedup_hash)`, checked on every create
- ⬜ `P3-05` Adapt the `linkedin-hiring-scraper` skill as a tool
- ⬜ `P3-06` Naukri and company career-page sources
- ⬜ `P3-07` Scheduled daily run *(needs Redis + Celery, below)*

**UI**
- ✅ `P3-08` Job Search screen built (multi-field search + facets)
- ✅ `P3-09` Shortlist / Match Review screen built
- ✅ `P3-10` Job Details screen built
- ⬜ `P3-11` Wire all three screens off `search.json` and onto the job API

**Infrastructure**
- ⬜ `P3-12` Redis + Celery for scheduling

**Sequence that matters:** one source working end to end beats four half-built connectors. The
Indeed connector plus content-hash dedup is the smallest thing that makes the three screens real.

---

## 5. Phase 4 — Applications & Settings
⬜ **API only.** The tracking half of the product, plus the preferences that will later drive
discovery.

**API**
- ✅ `P4-01` `application` module: stage, record fill, status transitions, answer bank
- ⬜ `P4-02` **Rebuild a preferences store for Settings.** `profile.preferences` was removed
  on 2026-09-11, so target roles, locations, company preference and discovery schedule have
  nowhere to live
- ⬜ `P4-03` Follow-up draft generation on an interval
- ⬜ `P4-04` Google Sheet sync

**UI**
- ✅ `P4-05` Staged Applications screen built
- ✅ `P4-06` Pipeline board built
- ✅ `P4-07` "Pending your review" banner built
- ✅ `P4-08` Settings screen built
- ⬜ `P4-09` Wire all three screens onto the application API and real counts
- ⬜ `P4-10` Wire the Settings screen onto that store, once it exists

**The preferences store is new work, not a wiring job** — that screen has no backend at all today.

---

## 6. Phase 5 — LLM integration & resume rectification
⬜ **not started.** The first intelligence in the product, called directly from the API. Still no
agents and no orchestration — deliberately, so a wrong answer stays debuggable.

**API**
- ✅ `P5-01` `match` module: write score and keywords, record the user's selection
- ✅ `P5-02` `resume` module: versioned `.tex` + selection set, rejects unselected keywords
- ⬜ `P5-03` Structured keyword extraction from a JD
- ⬜ `P5-04` Present / Missing keyword diff against the profile
- ⬜ `P5-05` Risk-flag detection (seniority mismatch and similar)
- ⬜ `P5-06` Embed the JD, `$vectorSearch`, compute a match score *(needs Atlas, below)*
- ⬜ `P5-07` Incorporate **only** the keywords the user ticked
- ✅ `P5-08` Version each `.tex` per job id: `version` on `resumes`, unique per
  `(job_id, version)`, incremented from the latest on every store

**UI**
- ✅ `P5-09` Keyword Selection screen built, starting with nothing checked (FR-2.5)
- ⬜ `P5-10` Wire it onto real match data instead of `matches.json`

**Infrastructure**
- ⬜ `P5-11` Pick and validate a local LLM; confirm tool-calling reliability
- ⬜ `P5-12` Atlas free tier + `$vectorSearch` index. *Not partial any more: the local
  chunk store this counted as half-done was removed on 2026-09-11, so nothing vector
  exists on either side*

**Guardrail**
- ⬜ `P5-13` No-fabrication test cases

**The guardrail is the point of this phase.** Tailoring from ticked keywords only, and the tests
proving it, are what make "no fabrication" real rather than aspirational — and neither can be
claimed while the API has no test suite.

---

## 7. Phase 6 — RAG & retrieval
⬜ **not started.** Tailoring and scoring should work against what your resume actually says, not
against the whole document stuffed into a prompt. This is the retrieval layer that makes that true.

**API**
- ⬜ `P6-01` RAG second hop: `resume_chunk_text` and the local text fetch by `chunk_id`
  *(this existed and was removed on 2026-09-11; it comes back here)*
- ⬜ `P6-02` Chunk the profile into retrievable units, section by section
- ⬜ `P6-03` Re-index on profile edit, so retrieval never serves stale text

**AI tier**
- ⬜ `P6-04` Embed chunks and store vectors in Atlas — **ids and vectors only, never prose**
- ⬜ `P6-05` Two-stage retrieval: `$vectorSearch` top ~50 → fetch text from `server` → rerank
  → top ~5

**Infrastructure**
- ⬜ `P6-06` Atlas free tier + `$vectorSearch` index, dimension matching the embedding model

**The split store is the point.** Atlas holds vectors and `chunk_id`s; the text stays in local
MongoDB. That is why retrieval needs two hops, and why the chunk store is a prerequisite rather
than an optimisation.

---

## 8. Phase 7 — MCP tool servers
⬜ **not started.** The agents in Phase 8 reach the outside world only through these, so they come
first.

**AI tier**
- ⬜ `P7-01` `jobpilot_api` — the one way agents read and write structural data, over HTTP
- ⬜ `P7-02` `latex` — render a tailored `.tex` from a template and a profile
- ⬜ `P7-03` `job_search` — Google CSE / SerpAPI behind one tool interface
- ⬜ `P7-04` `indeed` and `linkedin` source servers
- ⬜ `P7-05` `browser` — Playwright, for discovery only
- ⛔ `P7-06` MongoDB MCP Server. *Superseded: agents go through `jobpilot_api` over HTTP
  instead, so there is one validation boundary and no DB credentials in the agent process*

---

## 9. Phase 8 — Agents & orchestration
⬜ **not started.** Phases 3 and 5 do discovery and matching as plain endpoints. This phase turns
them into agents under a supervisor that can pause for a human.

**AI tier**
- ⬜ `P8-01` Job Discovery agent — scheduled, multi-source, dedup-aware
- ⬜ `P8-02` JD Match & Score agent — extraction, diff, scoring over RAG
- ⬜ `P8-03` Resume Tailor agent — selected keywords only, rendering through the `latex` server
- ⬜ `P8-04` Tracking & Follow-up agent — status transitions and interval drafts
- ⬜ `P8-05` LangGraph supervisor wiring all agents with shared state
- ⬜ `P8-06` **Human-approval interrupts** at keyword selection and application review
- ⬜ `P8-07` Retry and error handling per agent step

**UI**
- ⬜ `P8-08` Surface an interrupt in the dashboard — the approval gate needs somewhere to happen

**The approval interrupts are not a feature, they are the guardrail.** The supervisor must be unable to run past those
two interrupts; see the Design Principles in the README.

---

## 10. Phase 9 — Application agent & Chrome extension
⬜ **not started.** The last manual step: filling the form. Fills, never submits.

**Extension**
- ⬜ `P9-01` Scaffold (Manifest V3, content script, background worker, popup)
- ⬜ `P9-02` Field detection by label / ARIA / placeholder heuristics
- ⬜ `P9-03` LLM fallback for ambiguous fields
- ⬜ `P9-04` Highlight every filled field for review
- ⬜ `P9-05` Manual resume-attach flow
- ⬜ `P9-06` Workday / Greenhouse / Lever field patterns
- ⬜ `P9-07` LinkedIn Easy Apply

**API**
- ⬜ `P9-08` Serve job context and the Q&A answer bank to the extension
- ⬜ `P9-09` Application agent coordinating the fill from the `ai` tier

**Runs in your real browser session**, not an automated one — more reliable against ATS platforms,
and it keeps you in the loop by construction.

---

## 11. Phase 10 — Eval, guardrails & observability
⬜ **not started.** The phase that turns "it seems to work" into something measured. Everything
above is unprovable until this exists.

**Eval**
- ⬜ `P10-01` Ragas suite: **faithfulness** (the automated no-fabrication check), context
  precision and recall
- ⬜ `P10-02` Eval datasets built from real JDs and real profile content
- ⬜ `P10-03` A **local** judge model, so evaluation does not leak what generation protects

**Guardrails**
- ⬜ `P10-04` No-fabrication test cases
- ⬜ `P10-05` No-auto-submit test cases
- ⬜ `P10-06` The API test suite *(also in §13 — it blocks every phase, not just this one)*

**Observability**
- ⬜ `P10-07` Langfuse or Phoenix, self-hosted

---

## 12. Phase 11 — Daily use & polish
⬜ **not started.** The phase that only real usage can write.

- ⬜ `P11-01` Bug fixes from actually running the daily workflow
- ⬜ `P11-02` Q&A answer-bank refinement from real applications
- ⬜ `P11-03` Performance and cost tuning on the local models
- ⬜ `P11-04` Cover letter generation *(stretch)*

---

## 13. Cross-cutting — true of every phase

- ✅ `CC-01` FastAPI app shell: thin `main.py`, localhost bind, CORS for web + extension
- ✅ `CC-02` Beanie documents for every local collection, `ObjectId` keys
- ✅ `CC-03` React frontend, built in v1 instead of Streamlit/Gradio *(closed — see
  deviation 1)*
- ⬜ `CC-04` **Test suite for the API and its guardrails.** Removed on request; blocks the §15
  Definition of Done in every phase above
- ⬜ `CC-05` CI/CD via GitHub Actions (lint and test on push)

**The test suite is now the one that should not wait.** Server-side token enforcement closed in
Phase 1; the suite does not block building the next feature, but it should close before this is
used against real job applications — nothing above is verified by anything that runs on its own.

---

## 14. Implementation status

The dashboard UI was built ahead of the backend. `server/` is now built — eight modules, 51
endpoints, 13 collections, every one of them behind a bearer token. Sign-in and My Details run
against it end to end and hold real data; **the other eight screens still render from a JSON
fixture** in `app/web/src/data/`. No story meets the §10 Definition of Done, because the §15
test-case requirement is unmet everywhere: `server/` has no tests and there is no CI.

Audited against the codebase on 2026-09-13. Counts: **41 ✅ · 67 ⬜ · 2 ⛔** of 110 tasks.

`ai/` and the Chrome extension do not exist yet, so nothing agentic runs.

| Built | Backed by |
|---|---|
| Pipeline board · Shortlist · Staged Applications · Job Search · Job Details · Settings | `board.json` `search.json` `applications.json` `settings.json` |
| Keyword Selection — starts with nothing checked, per FR-2.5 | `matches.json` |
| Resume Preview — Preview / Diff / Source tabs, `.tex` download | `resume.json` + `templates/base_resume.tex` |
| **Login · Signup · sign-out · route guard** | **live — `POST /api/account/{signup,login}`, JWT in `sessionStorage`, mirrored into Redux** |
| **My Details — identity, experience, education, skills, certifications** | **live — `getAccount` + the five profile endpoints on load, one Save writes them all back. Only the "Indexed for retrieval" panel still reads `profile.json`; chunking is Phase 6** |

**Five deviations from this document, recorded deliberately:**

1. **Next.js, not Streamlit/Gradio.** The original plan named Streamlit or Gradio and
   deferred a React frontend to v2. The dashboard was built directly in Next.js + Tailwind, matching
   the stack in `CLAUDE.md` and doc 03. That path is therefore **closed, not deferred**, and the
   Streamlit/Gradio path was never taken.
2. **Templating went to `{{TOKEN}}` replacement, not Jinja2.** The `template` module renders
   uploaded `.tex` files by substituting `{{FULL_NAME}}`, `{{CONTACT}}` and the rest — see
   `modules/template/service.render`. There is no `jinja2` dependency, and `templates/base_resume.tex`
   now carries only *comments* describing `\VAR{}`/`\BLOCK{}`, with no such markers in it and nothing
   reading the file. The six `templates/Template*/` designs use `{{TOKEN}}` and are what the module
   expects. **No output of this pipeline has been compiled by a TeX engine** — its LaTeX validity is
   still unverified, and the `templates` collection is empty, so nothing has been uploaded yet either.
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
