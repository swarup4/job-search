# Project Roadmap

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | v1.7 — eleven phases, application first then agents. Phases 1 and 5 done; one Atlas cluster and hosted-only inference as of 2026-09-19 |
| **Updated** | 2026-09-19 |

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
| [2](#3-phase-2--resume-generation--download) | A resume built from that profile, downloadable | 🚧 `.tex` and PDF both download; three tasks left |
| [3](#4-phase-3--job-scraping-search--shortlist) | Real jobs in the system, searchable and shortlistable | 🚧 capture and parse land; connectors open |
| [4](#5-phase-4--applications--settings) | Tracking what you applied to, and the preferences driving it | ⬜ API only |
| [5](#6-phase-5--llm-integration--resume-rectification) | A resume rectified against a specific job | ✅ done |
| [6](#7-phase-6--rag--retrieval) | Retrieval over your own resume | ⬜ not started |
| [7](#8-phase-7--mcp-tool-servers) | The tool servers agents reach the world through | ⬜ not started |
| [8](#9-phase-8--agents--orchestration) | LangGraph agents under a supervisor, with approval interrupts | ⬜ not started |
| [9](#10-phase-9--application-agent--chrome-extension) | Form autofill in your own browser session | 🚧 extension fills and captures; the two LLM tasks wait on `ai/` |
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
- ✅ `P1-07` **Every collection is keyed by `userId`** except `templates`, which is global:
  `jobs`, `job_descriptions`, `matches`, `resumes`, `applications` and `answer_bank` each carry
  the owning account, and every query filters on it. Another user's id reads as 404, never 403 —
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
🚧 **downloads work, three tasks left.** Turn the profile into a document you can send. No LLM in
this phase — it is templating, not intelligence.

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
- ✅ `P2-07` Download the generated `.tex`. The Resume screen offers it straight from the render;
  `GET /template/download/{templateId}` serves the same source as a file, so a caller outside the
  browser does not have to unescape it out of JSON
- ✅ `P2-08` **PDF compilation and download.** `GET /resume/base/pdf` compiles the *stored* `.tex`
  with pdflatex and returns `application/pdf` — stored rather than re-rendered, so the PDF is the
  document on screen. `modules/resume/compile.py` runs it in a temp dir with `-no-shell-escape`
  (an uploaded template is uploaded LaTeX), `-halt-on-error` and a 30s timeout, surfaces the real
  LaTeX error on failure, and answers 503 with an install hint where no TeX engine exists. Setup:
  `docs/07-PDF-Setup-macOS.md`. **This contradicts FR-4.4 and invariant 5, which still say `.tex`
  only — both now need amending**
- ✅ `P2-13` `base_resumes` collection — one default resume per user: the chosen template and
  the `.tex` it produced, stored verbatim. `GET`/`PUT /resume/base`

**UI**
- ✅ `P2-09` Resume Preview screen built: Preview / Diff / Source tabs
- ⬜ `P2-10` Point the Resume Preview screen at a real render instead of `resume.json`
- ✅ `P2-11` Template picker in the dashboard — preview image per template, on the Resume screen
- ✅ `P2-14` **Resume screen** (`/resume`): pick a template, see your own details rendered into
  it, submit it as the default resume. The preview parses the rendered `.tex` in the browser
  (`util/texResume.js`), so the page and the stored document are the same string
- ⬜ `P2-15` **`Template2_BoldHeaderBand` has two contact links hardcoded in its `.tex`**
  (`linkedin.com/in/swarup-saha-d7`, `github.com/swarup4`), printed after `{{CONTACT}}`. Every
  user rendering that template gets them
- ✅ `P2-16` **Resume review screen** (`/resume/preview`): where submitting lands. Shows the
  stored resume, and **Regenerate** re-renders the same template from My Details and saves it —
  the stored `.tex` is a snapshot and does not follow later profile edits
- 🟡 `P2-17` **Rectification chat panel** on the review screen — laid out, deliberately inert.
  The composer, the suggested prompts and Send are disabled behind the usual "not connected"
  footer; wiring it is adding the call, not rebuilding the panel. Needs the `ai` tier (Phase 5)

**Verification**
- ✅ `P2-12` **A rendered `.tex` compiles under a TeX engine.** Verified 2026-09-17 on BasicTeX /
  TeX Live 2026: **all six** templates rendered from a real `getProfile` payload through
  `service.render` and compiled with pdflatex, 70–78 KB each. Setup and the package list:
  `docs/07-PDF-Setup-macOS.md`. The unfilled `templates/Template*/` files still cannot compile
  directly, and never could: the `_` in `{{FULL_NAME}}` is math-mode-only, so `render` has to
  run first

**PDF compilation was promoted** from the v1 stretch list: "generate and download" is hollow if the
output is a `.tex` the reader cannot open. Closed 2026-09-17 with pdflatex. The TeX engine is an
external prerequisite rather than a dependency — absent, the endpoint answers 503 with an install
hint. **Invariant 5 and FR-4.4 still forbid this and need amending.**

---

## 4. Phase 3 — Job scraping, search & shortlist
🚧 **one source works end to end.** Get real jobs into the system so the screens that already
exist have something to work on. Capture and the parse into a `Job` both land; the connectors,
the scheduler and the screen wiring are still open.

**API**
- ✅ `P3-01` `job` module: create with dedup-hash check, list by status, shortlist toggle
- ⬜ `P3-02` Indeed MCP connector
- ⬜ `P3-03` Google CSE / SerpAPI search
- ✅ `P3-04` Dedup on content hash, unique per `(userId, dedupHash)`, checked on every create:
  sha256 over `source` + `refId` where the board gives one, else title + company + location.
  The JD prose left `jobs` in the 2026-09-19 split and can no longer be part of the seed
- ⬜ `P3-05` Adapt the `linkedin-hiring-scraper` skill as a tool
- ⬜ `P3-06` Naukri and company career-page sources
- ⬜ `P3-07` Scheduled daily run *(needs Redis + Celery, below)*
- ✅ `P3-13` **`job_description` module**, renamed from `capture` on 2026-09-19. The
  `job_descriptions` collection holds the page as markdown (`jdText`), the HTML the job page
  renders (`htmlString`) and the `embedding` behind search, plus `url`, `pageTitle`, `region`,
  `links`, `textLength`, `contentHash`, `status` and a nullable `jobId`. `POST`/`GET
  /job-description`, `GET /job-description/{id}`, and `link` / `status` / `embedding` writes.
  Dedup copies `P3-04` — sha256 over url + text, unique per `(userId, contentHash)` — and a
  repeat returns `duplicate: true` rather than 409, because recapturing an unchanged page is
  not an error
- ✅ `P3-14` **Parse a capture into a `Job`.** `ai/agents/parsing.py` reads the stored markdown,
  writes the listing with `source: career_page`, and links the two. The model proposes and the
  page decides: a title or company not present verbatim refuses the parse, a technology the page
  never names is dropped from `requirements`, an unfindable requisition id is dropped, and a page
  that is not one posting is marked `discarded` rather than written. 9 tests in `ai/tests/`

**UI**
- ✅ `P3-08` Job Search screen built (multi-field search + facets)
- ✅ `P3-09` Shortlist / Match Review screen built
- ✅ `P3-10` Job Details screen built
- ⬜ `P3-11` Wire all three screens off `search.json` and onto the job API

**Infrastructure**
- ⬜ `P3-12` Redis + Celery for scheduling

**Sequence that matters:** one source working end to end beats four half-built connectors. The
Indeed connector plus content-hash dedup is the smallest thing that makes the three screens real.

**Capture is the cheapest first source.** `P3-13` needs no connector, no API key and no
scheduler — the user is already on the career page, and the browser is already authenticated to
it. It also sidesteps the `FR-1.4` robots.txt question entirely, because a human opening a page
they were invited to apply through is not a crawler. What it does *not* do is scale: it is one
page per click, which is why it complements `P3-02`/`P3-03` rather than replacing them.

**Markdown, not HTML.** Storing the converted text rather than the markup was a deliberate
narrowing: a posting is ~700 characters of markdown against ~1 MB of page, `jdText` is a text
field anyway, and markdown cannot express a `<style>` or a `<script>` so the exclusion needs no
filter to maintain. The cost is that it is **one-way** — the earlier design kept raw HTML so a
better extractor could be re-run over old rows, and that is no longer possible. A capture the
converter mangles is recaptured by hand. `region` and `textLength` exist to make that visible.

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
✅ **done.** The first intelligence in the product, called by hand from the AI tier. No agents and
no orchestration yet — deliberately, so a wrong answer stays debuggable.

`ai/` holds `config/` (settings + the one LLM client), `agents/matching.py`, `agents/tailoring.py`,
`mcp_servers/jobpilot_api/` and `tests/`. It imports nothing from `server` and reaches it over HTTP.

**API**
- ✅ `P5-01` `match` module: write score and keywords, record the user's selection
- ✅ `P5-02` `resume` module: versioned `.tex` + selection set, rejects unselected keywords
- ✅ `P5-03` Schema-constrained keyword extraction from a JD. A requirement whose quote is not in
  the JD is dropped rather than invented, and `mentions` is counted from the text. Added
  `GET /api/job/getJobDescription/{id}`
- ✅ `P5-04` Present / Missing diff against the **whole** profile. An "already have it" verdict
  with no evidence in the profile falls back to Missing — the safe direction to be wrong in
- ✅ `P5-05` Risk flags — seniority mismatch and similar. Surfaced, never selectable
- ✅ `P5-06` **Built differently from the task as written, deliberately:**
  - Score stays `coverage_score`. A JD↔resume cosine lands in one narrow band for every job in a
    field, and cannot be explained to someone asking why a job scored 62
  - No `$vectorSearch` here: the corpus is one resume, 25–40 spans, and the diff reads all of it
  - Embeddings bought `flag_near_misses` instead — a requirement the JD calls "agentic
    orchestration" and the profile calls "LangGraph multi-agent pipeline". Advisory: the keyword
    stays Missing and stays selectable
  - Voyage `voyage-4-lite`, ~900 tokens and ~$0.000018 per job. The one call carrying profile text
    off the machine, which is why NFR-3 reads "all generation is local" rather than absolute
  - ✅ **`near_miss_threshold` calibrated 2026-09-19 — and the old value was silently fatal.**
    At 0.70 nothing ever fired: on `voyage-4-lite` a true near-miss scores ~0.48, so the feature
    had never produced a single hint. Measured over 14 labels against 6 profile spans, related
    landed 0.368–0.544 and unrelated 0.219–0.324 — **the bands separate**, which bge-small never
    managed at any threshold. Set to **0.35**, above the midpoint because a missed hint costs
    nothing and a wrong one invites a claim the user cannot back. The sample is representative,
    not exhaustive; re-measure if the embedding model changes
  - Known waste: profile spans are re-embedded per job, though they change only with the profile
- ✅ `P5-07` Incorporate **only** ticked keywords. The `.tex` never reaches the model — it gets the
  current role and skill groups as data and answers with *placement*, which `tailoring.py` folds in
  line by line. No word may enter but the keyword and plain connectives, so a new metric, employer
  or tool is refused. A keyword with no honest home is declined and reported
- ✅ `P5-08` Version each `.tex` per job id, unique per `(jobId, version)`

**UI**
- ✅ `P5-09` Keyword Selection screen, starting with nothing checked (FR-2.5)
- ✅ `P5-10` Wired onto real match data — `getJob` + `getMatch` + `getShellCounts`, the two buttons
  resolving the interrupt. An unscored job says so; a reopened match starts unchecked again

**Infrastructure**
- ✅ `P5-11` **Validated against the hosted model, which is now the only one.**
  `Qwen/Qwen3-32B:nscale` on the HF router honours `strict: true` on every pipeline shape —
  checked 2026-09-19 against `Extraction`, `Diff`, `RiskReport` and `PlacementPlan`, the
  nested-array schemas being where a provider usually drops it. Quotes came back verbatim and
  the diff stayed conservative. **Ollama was dropped the same day**, so the local half of the
  pair is not pending work — `qwen3:14b` was never run and never will be.
  ⏱️ **Latency, measured:** 12–19s per call on nscale, so a full `rectify()` is ~45–60s a job.
  Fine by hand, worth knowing before `P8-01` schedules it in bulk
- ✅ `P5-12` `$vectorSearch` index on `job_descriptions.embedding` — 1024 dimensions (the
  `voyage-4-lite` default), cosine, with `userId` as a filter field so a search scopes to one
  account. Created by `server/migrate_job_descriptions.py`, which also moved `captures` across

**Guardrail**
- ✅ `P5-13` No-fabrication tests — 12 in `server/tests/` against a throwaway database, 32 in
  `ai/tests/`. A resume cannot be stored before the gate is answered, a skip is not a selection, a
  re-score reopens the gate, and a rewrite inventing a metric or employer is declined

### Decisions (2026-09-18)

**One OpenAI-compatible path.** `config/llm.py` is a single `generate(prompt, schema)` over
`httpx`. Pointing it elsewhere is three environment values, not a provider abstraction:

| | value |
|---|---|
| `LLM_BASE_URL` | `https://router.huggingface.co/v1` |
| `LLM_API_KEY` | `${HF_TOKEN}` |
| `LLM_MODEL` | `Qwen/Qwen3-32B:nscale` |

**Pin the provider** (`:nscale`) — `strict: true` support varies between them, and an unpinned
router drops it silently, which surfaces as intermittent parse failures rather than as a
configuration error. Disable thinking mode.

**Ollama was dropped on 2026-09-19.** The plan had been local-for-development and hosted-for-real,
with Ollama as the offline fallback. It was never installed on the working machine, so the local
half was validated only once, on `llama3.2:latest`, and never on the `qwen3:14b` the plan named.
Keeping an untested fallback in the docs was worth less than saying plainly that there is one path.

**Context discipline — what each step may see:**

| Step | Sees | Tokens |
|---|---|---|
| `P5-03` extraction | JD + schema | ~1,200 |
| `P5-04` diff | **the whole profile** | ~2,600 |
| `P5-05` risk flags | JD + profile summary | ~1,500 |
| `P5-07` tailoring | **current role + skills, no LaTeX** | ~1,300 |

`P5-04` stays wide on purpose: RASA sits in the LTI role and Angular.js in Mphasis, so a diff seeing
only the current role would mark both Missing and invite the user to add what they already have.

Of `base_resume.tex`, only the skills table (350 tokens) and the current role (447) are mutable —
797 of a 2,284-token body. The model never sees the preamble, education, certifications or the six
closed-out roles, so it cannot alter them. A guardrail as much as an economy.

**Cost** ~$0.00096/job, ~$0.10 per hundred. **Provenance:** `Match.modelName` records source and
model; scores from different models are not comparable.

**Now settled, and it went the other way.** Hosted inference contradicts SRS NFR-3 and invariant 3,
which say all inference is local. That was deferred while Ollama was still the default; with Ollama
gone it is simply true that **every JD, profile span and resume line in a prompt leaves the
machine**. README §"All generation runs locally", SRS NFR-3 and doc 03's Ollama/vLLM compute
section are now wrong and need amending — this is a privacy claim, not a nicety.

---

## 7. Phase 6 — RAG & retrieval
⬜ **not started.** Tailoring and scoring should work against what your resume actually says, not
against the whole document stuffed into a prompt. This is the retrieval layer that makes that true.

**API**
- ⬜ `P6-01` `resume_chunks` — chunk text and its vector on one document
  *(a text-only version existed and was removed on 2026-09-11)*
- ⬜ `P6-02` Chunk the profile into retrievable units, section by section
- ⬜ `P6-03` Re-index on profile edit, so retrieval never serves stale text

**AI tier**
- ⬜ `P6-04` Embed each chunk and store the vector beside its text
- ⬜ `P6-05` Retrieval: `$vectorSearch` top ~50 → rerank → top ~5

**Infrastructure**
- ⬜ `P6-06` `$vectorSearch` index on the chunk collection, dimension matching the model
  *(the cluster and the pattern are already there — see `P5-12`)*

**One store, one hop.** The earlier design split vectors into Atlas and kept text in a local
MongoDB, which is why this phase used to need two hops and a `chunk_id` join. Everything is one
Atlas cluster as of 2026-09-19, so a chunk carries its own text and a search returns it.

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
🚧 **the extension fills forms.** The last manual step, now automated up to the Submit button.
Both remaining tasks need an LLM, so they wait on Phases 6–8.

**Extension**
- ✅ `P9-01` Scaffold (Manifest V3, content script, background worker, popup)
- ✅ `P9-02` Field detection by label / ARIA / placeholder heuristics
- ⬜ `P9-03` LLM fallback for ambiguous fields — **blocked on `ai/`**
- ✅ `P9-04` Highlight every filled field for review, and an **in-page review panel** for the rest —
  docked into the application page, not the popup, because a popup closes the moment you click the
  form and that is exactly when the unanswered questions have to be readable
- ✅ `P9-05` Resume attach — automatic, with the manual fallback as the exception
- ✅ `P9-06` Workday / Greenhouse / Lever field patterns
- 🟡 `P9-07` LinkedIn Easy Apply — fills the open step; does not click **Next**
- ✅ `P9-10` Report the fill back: `fieldsFilled`, `screeningAnswers`, and the user's own answers
- ✅ `P9-11` **`applicant_profile` collection** — the standing answers a form asks for and a resume
  never carries: structured address, notice period, salary, work authorisation, sponsorship,
  relocation, total experience, EEO. `GET`/`PUT /application/applicant`, one per user, upsert.
  The extension reads it on every fill and prefers it over `profile` for form fields — `city` is a
  form box, `profile.location` is a resume line, and only one of them belongs in each

- ✅ `P9-12` **Capture button.** One button in the popup below "Fill this form": it stores the
  current career page against your account via `P3-13`, now `POST /job-description`. Reuses
  `ensureInjected()` in `background.ts`, which already falls back to
  `chrome.scripting.executeScript` for any page
  outside the four declared boards — so **no manifest change**. `activeTab` is conferred by the
  user opening the popup, which is the same gesture that starts the capture; `<all_urls>` would
  buy nothing here and cost the "read all your data on all websites" install warning
- ✅ `P9-13` **Extraction to markdown**, in `features/capture/`, via `turndown`. Region first:
  `main` / `[role=main]` / `article`, else a link-density-penalised largest-text-block
  heuristic, else `body` — and whichever matched is recorded in `region`, so a bad capture is
  legible as bad rather than silently wrong. Then furniture (`nav`, `footer`, `aside`, and
  `related`/`cookie`/`share`-class blocks holding under 40% of the text) is removed from the
  *clone*, links are resolved against `document.baseURI`, and images and form controls are
  dropped. 400k-char ceiling on both sides: the extension refuses first with the measured size,
  `JobDescriptionCreate.jdText` carries `max_length` as the backstop
- ✅ `P9-14` Capture from frame 0 only, and **not** through `broadcast()`/`merge()` — those are
  fill-shaped and typed to `FrameResult`. The `capture` arm widened the content listener's
  reply type to `Reply<FrameResult | CapturePayload | null>`, which `npm run typecheck`
  enforced across every caller

**API**
- ✅ `P9-08` Serve job context and the Q&A answer bank to the extension
- ⬜ `P9-09` Application agent coordinating the fill from the `ai` tier — **blocked on `ai/`**

**Runs in your real browser session**, not an automated one — more reliable against ATS platforms,
and it keeps you in the loop by construction.

**No answer is ever invented.** A field the profile cannot answer and the answer bank has not seen
comes back as a pending question in the popup, outlined amber on the page, for you to answer in your
own words. That is what `P9-03` will soften — not replace: an LLM suggestion still has to be a
suggestion. The profile deliberately holds no cover letter, work-authorisation or EEO data, so those
questions always come to you.

**Three known limits.** Workday and LinkedIn are multi-step wizards, and one pass fills the step on
screen only — nothing here navigates a form. The answer bank is still read-only over HTTP
(`upsert_answer` exists in `application/service.py` with no route), so a one-off answer typed in the
popup fills the field and is recorded on the application, but is not saved for next time. And
`applicant_profile` has **no UI** — it is populated through `/docs` or curl until a Settings screen
reaches it, which is `P4-10`'s neighbour rather than part of this phase.

**Where capture will fail, and how you will know.** A DOM walk does not cross a shadow root, so a
posting rendered inside one stores a near-empty shell; the same is true of a posting in a
cross-origin iframe, since `P9-14` reads frame 0 only. An SPA that has not painted yet captures
whatever *has*. A sign-in wall captures cleanly and looks like a success. All four share one tell —
`textLength` near zero — which is why it is a stored column and why `JobDescriptionRead` carries it while
dropping the text itself. `region: "body"` is the second tell: it means no rule was confident.
Unlike the HTML design this replaced, none of these are repairable by re-running a better extractor
later — the markup is not kept. They are recaptured by hand.

**`applicant_profile` is not `P4-02`.** Those are discovery preferences — which jobs to go looking
for. These are answers about you, read only when filling a form. Two stores, two purposes; merging
them would put "target salary band for search" and "what I told Wells Fargo I earn" in one field.

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

The dashboard UI was built ahead of the backend. `server/` is now built — eight modules, 63
endpoints, 15 collections, every one of them behind a bearer token. Sign-in and My Details run
against it end to end and hold real data; **the other eight screens still render from a JSON
fixture** in `app/web/src/data/`. No story meets the §10 Definition of Done, because the §15
test-case requirement is unmet everywhere: `server/` has no tests and there is no CI.

Audited against the codebase on 2026-09-13; Phase 2 re-audited 2026-09-14, and again on
2026-09-17 for `P2-07`, `P2-08` and `P2-12`. Counts predate the Phase 2 additions
(`P2-13`…`P2-17`) and the two download endpoints, and are due a recount.

`ai/` exists as of 2026-09-18 but holds no graph: Phase 5's two capabilities are called by hand, so
nothing agentic runs yet. The Chrome extension is built (Phase 9).

| Built | Backed by |
|---|---|
| Pipeline board · Shortlist · Staged Applications · Job Search · Job Details · Settings | `board.json` `search.json` `applications.json` `settings.json` |
| Keyword Selection — starts with nothing checked, per FR-2.5 | `matches.json` |
| Resume Preview — Preview / Diff / Source tabs, `.tex` download | `resume.json` + `templates/base_resume.tex` |
| **Login · Signup · sign-out · route guard** | **live — `POST /api/account/{signup,login}`, JWT in `sessionStorage`, mirrored into Redux** |
| **My Details — identity, experience, education, skills, certifications** | **live — `getAccount` + the five profile endpoints on load, one Save writes them all back. Only the "Indexed for retrieval" panel still reads `profile.json`; chunking is Phase 6** |
| **Resume — template picker, render, submit as default** | **live — `GET /api/template`, `GET /api/template/render/{id}`, `PUT /api/resume/base`** |
| **Resume review — stored resume, Regenerate, `.tex` and PDF download** | **live — `GET /api/resume/base`, `GET /api/resume/base/pdf` (pdflatex). The chat panel beside it is layout only** |

**Six deviations from this document, recorded deliberately:**

1. **Next.js, not Streamlit/Gradio.** The original plan named Streamlit or Gradio and
   deferred a React frontend to v2. The dashboard was built directly in Next.js + Tailwind, matching
   the stack in `CLAUDE.md` and doc 03. That path is therefore **closed, not deferred**, and the
   Streamlit/Gradio path was never taken.
2. **Templating went to `{{TOKEN}}` replacement, not Jinja2.** The `template` module renders
   uploaded `.tex` files by substituting `{{FULL_NAME}}`, `{{CONTACT}}` and the rest — see
   `modules/template/service.render`. There is no `jinja2` dependency, and `templates/base_resume.tex`
   now carries only *comments* describing `\VAR{}`/`\BLOCK{}`, with no such markers in it and nothing
   reading the file. The six `templates/Template*/` designs use `{{TOKEN}}` and are what the module
   expects. Rendered output **is** now compiled by a TeX engine — see `P2-12` and
   `docs/07-PDF-Setup-macOS.md`. The six designs were imported into the `templates` collection on
   2026-09-14 via `import_templates.py`, and the Resume screen renders and stores them.
3. **Authentication was built**, which PRD §4, SRS §42 and `.claude/rules/server-api.md` all rule out
   on single-user grounds. As of 2026-09-11 the screens are no longer interface-only: accounts are
   stored with argon2 hashes, login and signup both issue a JWT, and every dashboard route redirects
   to `/login` without one. **Those three documents are now wrong and need amending** — the decision
   went the other way. Reopened as in scope.
4. **`profile.preferences` and `resume_chunk_text` were removed** (2026-09-11) to keep the profile
   module focused on resume material. The Settings screen therefore has no backend, and chunked
   retrieval no longer exists — it is rebuilt in Phase 6. Doc 06 and doc 03 still describe both.
6. **One store, not two.** The design split structural data into a local MongoDB and vectors into
   Atlas, with `job_id` and `chunk_id` crossing the boundary. As of 2026-09-19 everything is one
   Atlas cluster: `captures` became `job_descriptions`, which carries its own `embedding`, and
   `events` was dropped for having no writer. Doc 06 and its ER diagram were redrawn; doc 03 was
   not.
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

- ~~PDF compilation of tailored `.tex` resumes~~ — **promoted into Phase 2 and closed there**
  (`P2-08`, 2026-09-17). Base resume only; tailored `.tex` gets the same treatment when Phase 5
  produces one
- Cover letter generation — carried in Phase 11
- LinkedIn Easy Apply full support — Phase 9 fills the open step; multi-step navigation still open
- A2A-based Application Agent as an independently scalable service
- Multi-device sync (if ever needed — would require revisiting the single-user Atlas-only vector store decision)
