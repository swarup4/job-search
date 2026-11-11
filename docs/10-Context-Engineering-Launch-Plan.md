# 10 — Context Engineering Review and Launch Plan

| | |
|---|---|
| **Written** | 2026-11-10, revised the same day after a second full read of the code |
| **Reviewed against** | *Context Engineering — Complete Course Notes* (CampusX, 2026-09-v01) |
| **Code state** | branch `ai` at `44dcb5b` (application code identical to `main` at `e12f090`) |
| **Release shape** | Run and test locally first, then move to a server for a small, invited group of users in India |

Task ids (`LS-`, `CE-`, `EV-`, `MA-`, `FE-`, `SV-`) are new and do not clash with the roadmap's
`P*` / `CC-*` ids.

## Progress

*Updated 2026-11-10. Nothing is committed; the changes are in the working tree on branch `ai`.*

| Task | State | Evidence |
|---|---|---|
| `LS-01` Python 3.12 | done | installed through `uv`; both tiers' dependencies sync |
| `LS-05` Run both suites | **AI tier only** | 277 pass, 1 fails. The failure predates this work: `ai/.env.example` names a hosted model endpoint, which the repo's own guardrail test forbids. It needs the `LS-03` decision. The server suite was not run: it needs a local MongoDB, and this machine has none |
| `LS-06` Windows setup doc | done | [doc 11](11-Local-Setup-Windows.md) |
| `EV-01` Persist usage per call | done, server half untested | AI tier records step, model, prompt version, attempt, prompt / cached / completion tokens and time, and posts them when a run ends. New server module `llm_usage` stores them and serves `GET /api/llm-usage/summary` |
| `MA-01`, `MA-02` Per-user indexes | done, untested | `matches` and `resumes` are now unique per user. An existing database needs `server/migrate_per_user_indexes.py` |
| `MA-03` Two-account tests | written, not run | `server/tests/test_multi_account.py` |
| `MA-04` Per-user inventory lock | done | lock is per profile; two new tests |
| `CE-05` Budget the repair turn | done | a retry echoes at most 1,500 characters of the failed reply, and the budget check reserves room for it |
| `CE-08` Version every prompt | done | versions for compare, tailor, parse and details; stored on each match and tailored resume and in the usage log |
| Test fix | done | `test_voyage_is_imported_only_by_the_rag_clients` failed on Windows because of path separators |

**Next, and blocked on setup only you can do:** an Atlas cluster, a Voyage key and the model
choice (`LS-02`–`LS-04`), then the baseline run (`EV-00`). The prompt changes in `A3` are held
until that baseline exists, because they are judged against it.

**Not verified:** the server changes (`MA-01`–`MA-03`, the `llm_usage` module). They import, lint
and register their routes, but their tests need a MongoDB to run against.

---

## 1. Decisions

| # | Question | Answer |
|---|---|---|
| D1 | Hosted or local? | **Local first for testing, then a server.** The plan is split into Stage A and Stage B on that line |
| D2 | Privacy promise | **Acceptable as it is for now.** Only the false "all generation is local" line gets corrected (`SV-12`); no policy work is planned |
| D3 | Audience | **India, invited users only.** No public signup, no billing, no public Chrome Web Store listing |
| D4 | Build the LangGraph supervisor and MCP servers (roadmap Phases 7–8)? | **Yes, but built to a context budget.** See [step A6](#a6--agents-and-mcp-servers-built-to-a-context-budget-about-3-weeks) |

---

## 2. What already follows the framework

Keep these.

| Practice | Where |
|---|---|
| Each step is given a narrow view (the tailoring model never sees the `.tex`, education or closed-out roles) | `ai/agents/tailoring.py`, `ai/agents/matching.py` |
| Read once, store, reuse: the posting's brief and the profile's skill inventory are versioned and rebuilt only when stale. The brief is stored on the shared posting, so every user reuses it | `ensure_brief`, `ensure_inventory` |
| A requirement found word-for-word in the profile is decided in code and never sent to the model | `matching.compare` |
| Counting and scoring are done in code, not generated | `coverage_score`, `occurrences` |
| Text written by strangers is fenced in `<document>` tags, with a rule to ignore instructions inside | `config/llm.py` |
| Every quote the model returns is checked against its source and dropped if absent | `agents/evidence.py` |
| A prompt too large for the window is refused before it is sent | `check_budget` |
| System prompts contain no per-call values, which a prefix cache needs | all `*_SYSTEM` constants |
| Retrieval uses a measured similarity threshold, not a fixed top-k | `NEAR_MISS_THRESHOLD` |
| The same embedding model is used for queries and stored text; each chunk is one bullet, skill or credential | `rag/embeddings.py`, `server/modules/profile/chunking.py` |
| No tool-calling loop: code runs the sequence, so intermediate data never piles up in a context window | `agents/analysis.py` |
| The scraper checks robots.txt on every request, limits itself to two requests per host and backs off | `ai/sources/http.py` |

---

## 3. Gaps

### 3.1 Context engineering

| # | Gap | Evidence | Effect | Fix |
|---|---|---|---|---|
| G1 | The scoring prompt puts per-job text before per-user text | `matching._comparison_prompt`: requirements, inventory, job, candidate | In a scoring run the inventory and candidate blocks are the same on every call, but with job text in front nothing is shared and nothing can be cached. The question is also at the top, furthest from the answer | `CE-01` |
| G2 | Requirement labels are outside any fence | Same function; labels are taken from postings | Stranger-written text sits where instructions sit. The live injection tests cover the job block only | `CE-01` |
| G3 | The system prompt does not say what each block is | `COMPARE_SYSTEM` never names `skill_inventory`, `job` or `candidate` | The model must guess which block is evidence and which is the question | `CE-01` |
| G4 | The tailoring prompt has no tags and no untrusted-input rule | `tailoring.plan_placements`, `TAILOR_SYSTEM` | Keywords come from postings; bullets, groups and keywords run together | `CE-02` |
| G5 | Each posting is read by the model twice | Scraped: `analysis._details`, then `matching.build_brief`. Captured: `parsing.parse_description`, then `build_brief` | Up to 12,000–16,000 characters are sent and billed twice per posting | `CE-03` |
| G6 | Postings are cut by position, uncleaned | `text[:MAX_JD_CHARS]`, `page[:MAX_PAGE_CHARS]`; link URLs and images stay in | Noise is paid for, and a long page can lose its requirements section to the cut | `CE-04` |
| G7 | The budget check ignores the repair turn | `check_budget` counts one reply; `generate` resends the failed reply and asks again | For the inventory call (6,144-token reply), a profile over roughly 11,000 characters can overflow a 16,384-token window on retry. Ollama truncates without an error | `CE-05` |
| G8 | An embedding is bought per posting and never read | `analysis._embedding`; the only `$vectorSearch` in the server is over `resume_chunks` | Cost and delay on every analysis for no feature | `CE-06` |
| G9 | A full scoring run scores every job in the shared catalogue for the user | `scoring/service._execute` loops `list_unscored_jobs` until none are left; `match.unscored` applies no filter | Model spend grows as users × all jobs, including jobs outside the user's own roles and locations | `CE-07` |
| G10 | Chunks are embedded without their context | `chunking._add` embeds the bare bullet; role and company sit in `sourceRef` | "Cut latency by 40%" carries no stack or role, so a near-miss search cannot find it. The threshold was measured on 14 labels against 6 spans | `CE-10` |
| G11 | Two-stage retrieval has no caller | `rag.retrieve`, `rag.rerank` are called only from their own `__main__` | Built and tested, feeding nothing until the chat exists | `FE-03` |
| G12 | Only two of six prompts are versioned | `BRIEF_VERSION`, `INVENTORY_VERSION` only | A match cannot be traced to its prompt, and stale results are not rebuilt | `CE-08` |
| G13 | Usage is measured and thrown away | `track_usage` totals go to the log; no cached-token count, no timing | No cost per user and no baseline | `EV-01` |
| G14 | No evaluation set | Three live-model tests; no labelled postings | Prompt and model changes are judged by eye | `EV-02` |
| G15 | No conversation layer | `ResumeChat.jsx` is disabled; no thread storage or history handling | The first multi-turn feature has no design for growing history | `FE-03` |
| G16 | Nothing learns from the user | Profile holds facts only; `events` was dropped | Tailoring cannot improve from accepted and declined edits | `FE-04` |
| G17 | The answer bank cannot be written to | `application.service.upsert_answer` has no route and no caller; the extension only reads the bank | Answers typed during an application are saved on that application and never reused | `FE-02` |
| G18 | The extension matches questions by word overlap only | `app/extension/src/features/answerBank/index.ts` | A question worded differently from the stored one goes unanswered (roadmap `P9-03`) | `FE-02` |

### 3.2 Correctness with more than one account

These fail as soon as a second person uses the same database, including during local testing.

| # | Gap | Evidence |
|---|---|---|
| M1 | Only one user can have a match for a given job | `matches` has a unique index on `jobId` alone (`server/modules/match/models.py`), while jobs are shared. The second user's score for the same job is rejected by the database |
| M2 | Two users cannot both tailor the same job | `resumes` is unique on `(jobId, version)` (`server/modules/resume/models.py`); both start at version 1 |
| M3 | One analysis, one scoring and one discovery run at a time across all accounts | Module-level `_slot` in `ai/api/{analysis,scoring,discovery}/service.py`; a second user gets a 409 |
| M4 | The inventory build lock is shared by every user | `_building` in `ai/agents/inventory.py` |
| M5 | A run uses the user's 60-minute token and stops when it expires | `EXPIRED` handling in the same three services; a long scoring run cannot finish |

### 3.3 Server readiness

| # | Gap | Evidence |
|---|---|---|
| S1 | Anyone who can reach the server can sign up | `POST /account/signup` has no gate |
| S2 | The signing key has a hard-coded fallback | `os.environ.get("JWT_SECRET", "swarupjobs")` in `server/modules/account/security.py` |
| S3 | No password reset, no login rate limit; old refresh tokens stay valid after a refresh | `server/modules/account/` |
| S4 | Any signed-in account can change shared data | Jobs, descriptions, briefs, career sources and templates take `_: CurrentUser`. One account can overwrite a brief that every other user is scored against |
| S5 | Any signed-in account can read and clear the error log for all tiers | `server/modules/error_log/router.py` |
| S6 | Three things live on local disk | The error log is a file both tiers append to; tailored `.tex` files are written under `ai/output` and their path stored; template previews are files. These break when tiers run in separate containers |
| S7 | Both servers bind to loopback, CORS is hard-coded to localhost, and the API server runs with `reload=True` | `server/main.py`, `ai/main.py` |
| S8 | No Dockerfile, no CI | Repository root |
| S9 | The extension is built for localhost and its manifest only permits localhost | `app/extension/build.mjs`, `public/manifest.json` |
| S10 | Onboarding means typing a whole CV | My Details has no import |
| S11 | Personal and environment data in the repository | `server/seed_profile.json` (name, phone, email), `templates/*/Swarup_Saha_Resume.tex`, an Atlas hostname in `server/.env.example` |
| S12 | README and docs 01–03 describe a different system | README says `ai/` is empty and that all generation is local; setup docs assume macOS |

---

## 4. Stage A — Run and test locally

Durations are rough estimates for one or two developers. Re-estimate after `A1`.

### A0 — Get it running on this machine (2–3 days)

- [ ] `LS-01` Install Python 3.12 or newer, and MiKTeX or TeX Live for PDF download (set
  `PDFLATEX_BIN`). Node 22 and Ollama are already installed.
- [ ] `LS-02` Create a free MongoDB Atlas cluster and point `MONGODB_URI` at it. A local MongoDB
  is not enough: the near-miss search uses `$vectorSearch`, which only Atlas provides, so scoring
  fails on a local database whenever a requirement is missing.
- [ ] `LS-03` Choose the generation model and keep it for the whole of Stage A: either local
  Ollama (the code default, 16,384-token window) or the hosted router in `ai/.env.example`. Scores
  from different models are not comparable, so the baseline must use the model the server will use.
- [ ] `LS-04` Fill the three `.env` files (model, Voyage key, `JWT_SECRET`), start the three
  tiers, load the extension unpacked.
- [ ] `LS-05` Run both test suites and record the result. Fix anything that fails before changing
  code.
- [ ] `LS-06` Write the Windows setup steps into a short doc; the existing ones assume macOS.

**Exit:** sign up, add a profile, run discovery, analyse a job, tailor, download a PDF, fill one
application form. Both suites pass.

### A1 — Baseline (3–4 days)

- [ ] `EV-01` **Persist usage per model call.** In `ai/config/llm.py` `_record`, capture step,
  model, prompt version, prompt tokens, cached tokens when reported, completion tokens, attempts
  and elapsed time. Store them through a new server endpoint in an `llm_usage` collection keyed by
  `userId` and run id.
- [ ] `EV-00` **Record the baseline.** Score 50 real Indian postings against one profile. Save
  tokens, cost, time and retry rate per step.

**Exit:** a stored table of cost and time per step that later phases compare against.

### A2 — Second account works (2–3 days)

Do this before a second tester joins.

- [ ] `MA-01` Change the `matches` unique index to `(userId, jobId)`.
- [ ] `MA-02` Change the `resumes` unique index to `(userId, jobId, version)`.
- [ ] `MA-03` Add tests that create two accounts, score and tailor the same job from each, and
  check neither sees the other's match, resume, chunks or inventory.
- [ ] `MA-04` Lock the inventory build per user.

**Exit:** two accounts on one database can each score and tailor the same job.

### A3 — Fix the context in the existing pipelines (about 1.5 weeks)

- [ ] `CE-01` **Reorder and tag the scoring prompt.** Send blocks in this order: skill inventory,
  candidate digest, job, requirements. Put requirement labels in their own tag. Add three lines to
  `COMPARE_SYSTEM` naming each tag and which one is the question.
  *Check:* injection tests pass, including a new one with a hostile requirement label; from the
  second job of a run, cached tokens are above zero where the model server reports them.
- [ ] `CE-02` **Tag the tailoring prompt** and add `UNTRUSTED_RULE`; name the tags in
  `TAILOR_SYSTEM`.
- [ ] `CE-03` **Read each posting once.** Add experience, salary and job type to `BriefDraft`,
  verified by the existing `verify_details`. `analysis._details` becomes a copy from the stored
  brief. For captured pages, have the parse call return the brief fields too. Bump `BRIEF_VERSION`.
  *Check:* one model call per posting in `llm_usage`. If the larger schema lowers accuracy on
  captured pages, keep that parse separate.
- [ ] `CE-04` **Clean postings, then trim by section.** New `ai/agents/cleaning.py`: turn
  `[text](url)` into `text`, drop images, collapse blank and repeated lines. If still over budget,
  keep sections by heading (responsibilities, requirements, qualifications, skills) and drop
  benefits and legal text, instead of cutting at a character count. Run the evidence checks on the
  same cleaned text the model saw.
- [ ] `CE-05` **Budget the repair turn**: count a failed reply plus a second reply in
  `check_budget`, or resend only the validation error and a shortened copy of the failed reply.
- [ ] `CE-06` **Remove the unused posting embedding** from `analysis.analyze`. Bring it back with
  a feature that reads it.
- [ ] `CE-07` **Score only relevant jobs.** Filter `match.unscored` by the user's saved roles and
  locations, and cap a scoring run (analysis is already capped at 50).
- [ ] `CE-08` **Version every prompt** (`COMPARE_VERSION`, `TAILOR_VERSION`, `PARSE_VERSION`) and
  store the version on each match and tailored resume.
- [ ] `CE-09` **Batch the near-miss search**: one request carrying all label vectors instead of
  one request per label.

**Exit:** rerun `EV-00`. Target: prompt tokens per job down by at least a third, model calls per
job down from four to three or fewer, no loss of accuracy.

### A4 — Evaluation (about 1 week, overlaps A3)

- [ ] `EV-02` **Evaluation set.** 40–50 real Indian postings (different applicant-tracking
  systems and lengths; salary in LPA, notice periods) and 5–8 profiles. Label requirements, the
  four details, present/missing verdicts and true near misses.
- [ ] `EV-03` **Runner** in `ai/eval/`: requirement precision and recall, verdict accuracy, the
  rate of wrong "present" verdicts (the harmful direction), tailoring decline rate, tokens, time
  and cost per job, per prompt version and model.
- [ ] `CE-10` **Contextual chunks.** Embed each chunk with its role and company in front, while
  storing and showing the bare text. Re-measure `NEAR_MISS_THRESHOLD` on the evaluation set. Adopt
  only if related and unrelated scores separate more widely than now.
- [ ] `EV-04` Extend the live adversarial tests to at least one per prompt.
- [ ] `EV-05` CI (roadmap `CC-05`): lint and both suites on every push.

**Exit:** a prompt or model change produces a before-and-after report without manual checking.

### A5 — Features that need new context design (about 3 weeks)

- [ ] `FE-01` **Resume import.** Upload PDF or DOCX, convert to markdown, extract into the five
  profile collections with a schema-constrained call, check each value against the document as
  `parsing.py` does, and show the result for confirmation before saving.
- [ ] `FE-02` **Answer bank that grows, and smarter question matching.** Add the missing write
  route so an answer typed in the extension is saved to the bank. For a question the word-overlap
  lookup cannot answer: embed it, search the bank and profile chunks by threshold, and give the
  model only the question and the matches. It returns the key of a stored answer or "ask the
  user". It never writes a new fact and never answers legal or equal-opportunity questions.
- [ ] `FE-03` **Resume chat.** Stable content first:

  | Order | Block | Changes |
  |---|---|---|
  | 1 | System: role, rules, limits, guide to the tags | Never |
  | 2 | The user's learned rules and a profile digest | Once per session at most |
  | 3 | Conversation summary, then recent turns | Each turn |
  | 4 | Retrieved profile chunks and the resume section being edited | Each turn |
  | 5 | The user's message | Each turn |

  Store threads by id. Past a token threshold, summarise the middle into a state record
  (decisions, constraints with reasons, open items) and keep block 1 and the last few turns
  word for word. Retrieve with the existing `rag.retrieve`, by threshold. The model returns
  proposed edits as structured changes, checked by `tailoring.invented_words`, and the user
  accepts or rejects each. No tool calling is needed.
- [ ] `FE-04` **Memory.**
  - *Learned rules* (how to help this user): a keyed store updated in place, drawn from chat turns
    and from accepted or declined edits; all of it goes into block 2; visible and editable in
    Settings.
  - *Events* (what happened): an append-only collection written on tailor, apply, status change
    and follow-up; retrieved by relevance into block 4.
  - Build memory from the raw turns, never from a summary.

### A6 — Agents and MCP servers, built to a context budget (about 3 weeks)

Roadmap Phases 7–8 stay in, with one rule: **adding the graph and the tool servers must not make
any existing model call larger.** The baseline from `A1` is the measure.

The risk is concrete. The model window is 16,384 tokens. The course measured a browser-automation
MCP server at about 18,000 tokens of tool definitions and a GitHub server at about 17,600, each
more than the whole window. The design below keeps tool definitions away from the model unless the
model is the one choosing.

**Design rules**

| Rule | What it means here |
|---|---|
| Code routes fixed sequences; the model routes only open-ended requests | The pipeline graph (discover, analyse, score, tailor, track) uses fixed edges. Only the chat entry point uses a model to pick a route |
| Graph state carries ids and small results, never a growing message list | Each node builds its own prompt from state, exactly as the functions do today. No node inherits another node's conversation |
| A tool the model does not choose is called from code | Discovery, LaTeX rendering and API writes go through MCP as plain client calls. Their definitions and raw results never enter a prompt |
| The model sees only the tools for its current node | A fixed allow-list per node. Search-based tool loading is added only if one node needs more than about ten tools |
| Results are shaped where they are produced | Each tool returns only the fields its caller needs, pages long lists, and returns short structured errors, never a stack trace or a full log |
| Everything is measured | Tool-definition tokens and tool-result tokens are recorded in `llm_usage`, and a test fails when a node exceeds its budget |

**Tasks — orchestration**

- [ ] `AG-01` **Pipeline graph.** Wrap the existing functions as LangGraph nodes without changing
  their prompts: `sources.run_all`, `ensure_brief`, `ensure_inventory`, `compare`,
  `flag_near_misses`, `plan_placements` / `review` / `apply`. Edges are fixed. State holds user
  id, job id, run id and the structured outputs.
- [ ] `AG-02` **Checkpoints in the database.** Use a MongoDB checkpointer so a run survives a
  restart. This replaces the in-memory `_slot` objects and covers `SV-06`.
- [ ] `AG-03` **Two approval interrupts** (roadmap `P8-06`): after scoring, wait for keyword
  selection; before an application is marked applied, wait for the user. The server keeps its
  own checks (`SelectionGateNotPassed`, `Fabrication`, `SubmitNotConfirmed`), so the guarantee
  does not depend on the graph.
- [ ] `AG-04` **Retries per node** (roadmap `P8-07`), each within the node's token budget, with
  the retry counted in `llm_usage`.
- [ ] `AG-05` **Tracking and follow-up node.** Runs on a schedule, reads due follow-ups, and
  drafts a message grounded in the `events` history from `FE-04`. It drafts only; sending stays
  with the user.
- [ ] `AG-06` **Chat router.** One small model call classifies each chat message as a question
  about the user's data, a request to change the resume, a request to act (score, tailor, find
  jobs), or small talk. Small talk gets no retrieval and no tools. The rest go to the matching
  node with that node's tools only.

**Tasks — MCP servers**

- [ ] `MC-01` **`jobpilot_api` as a real MCP server.** Today it is an HTTP client with 30
  functions. Expose a small task-shaped set instead of one tool per endpoint, named in families
  (`job_search`, `job_get`, `match_get`, `resume_get`, `application_list`, `profile_get`,
  `status_get`). Each description says what it does, what its arguments mean and what it returns.
  Job lists come back paged, with a total and a has-more flag, as CSV with only the columns
  asked for. Counts and totals come from the existing `/status` endpoint, never from the model
  adding up rows.
- [ ] `MC-02` **`latex` server** with two tools, render and compile. Compile returns a document
  id and, on failure, the first error line only.
- [ ] `MC-03` **`job_search`, `indeed`, `browser` servers, called from code.** The discovery
  node invokes them directly. Page content is converted to markdown, cleaned by `CE-04`, and only
  then read by the parse prompt. Their tool definitions are never sent to the model.
- [ ] `MC-04` **`linkedin`.** Keep it to pages the user captures with the extension in their own
  session. Server-side scraping of LinkedIn risks account blocks and breaches its terms.
- [ ] `MC-05` **Filtering layer in the AI tier.** The AI tier is the MCP host: it holds every
  server's tools and passes each node its allow-list, converted once to the model's tool format.
  A call to a tool that is not loaded is answered with a short correction, not a silent failure.
  Any resources or prompts a server offers go through retrieval with a threshold, never straight
  into a prompt.
- [ ] `MC-06` **Budget tests.** Fail the suite if any node's tool definitions exceed 10% of the
  window, or if any tool result exceeds a set size without being paged or trimmed.
- [ ] `MC-07` **Tool-selection check.** Add chat requests with the expected tool to the
  evaluation set, and measure how often the chosen model picks the right tool with the right
  arguments. This is the roadmap's open "validate a local model's tool-calling" task.

**Exit:** the full pipeline runs as a graph with both approval interrupts and survives a restart;
tokens per job in `llm_usage` are no higher than after `A3`; the chat picks the right tool on the
evaluation set at an agreed rate.

---

**Exit of Stage A:** a new tester can sign up, import a resume, score jobs, tailor, download a
PDF and fill an application without typing a profile by hand; the evaluation report meets the
agreed accuracy; cost per job is known.

---

## 5. Stage B — Move to a server for invited users (about 2–3 weeks)

**Access**
- [ ] `SV-01` Invite-only signup: an invite code or an email allow-list checked in
  `account.service.sign_up`.
- [ ] `SV-02` Refuse to start when `JWT_SECRET` is missing; remove the fallback.
- [ ] `SV-03` Rate-limit login. Password reset can be an admin action for this group.
- [ ] `SV-04` An admin flag on accounts. Restrict career sources, template upload and the error
  log to admins.
- [ ] `SV-05` Give the AI tier its own credential for writing shared data (jobs, descriptions,
  briefs), so no user account can overwrite them.

**Runs**
- [ ] `SV-06` One run per user per type, with a global limit on how many run at once. Run state
  comes from the graph checkpoints (`AG-02`), so a restart loses nothing. For a small invited
  group this can stay in the AI process; add a queue and worker only if `llm_usage` shows the
  need.
- [ ] `SV-07` Issue a run-scoped token from the server so a run outlives the 60-minute login
  token.
- [ ] `SV-08` Run discovery on a schedule for everyone, since the catalogue is shared, and
  remove the per-user button or restrict it to admins.
- [ ] `SV-09` A daily model budget per user, enforced from `llm_usage`.

**Deployment**
- [ ] `SV-10` A Dockerfile for each of `server`, `ai` and `app/web`, and a compose file that runs
  them on one host behind HTTPS. TeX Live goes in the server image.
- [ ] `SV-11` Read bind address and CORS origins from the environment; turn off `reload`. Move
  the error log into the database, stop writing tailored `.tex` files to disk (the text is already
  stored), and move template previews into the database or object storage.
- [ ] `SV-12` Remove personal data and the Atlas hostname from the repository. Correct the
  README: `ai/` exists, and generation is not local when a hosted model is configured.
- [ ] `SV-13` Build the extension against the server URLs with matching host permissions, and
  hand the build to invited users directly.
- [ ] `SV-14` Backups for the Atlas cluster, error tracking, and a page showing cost per user per
  day from `llm_usage`.

**Rollout**
- [ ] `SV-15` Invite the first few users. Watch: signup to first tailored resume, reports of
  wrong "present" verdicts, declined-keyword rate, cost per active user, time per job.

**Exit:** two invited users can run analysis at the same time on the server, a restart mid-run
loses nothing, and no fabricated content appears in any tailored resume.

---

## 6. Not in this release

| Item | Why |
|---|---|
| Billing, public signup, public Chrome Web Store listing | The audience is a small invited group (D3) |
| Privacy policy and terms | Accepted as is for now (D2); revisit before any wider release |
| Sign-in with Google, account deletion and export | Needed for a public launch, not for invited testers |
| A model-driven supervisor that picks every pipeline step | The pipeline is a fixed sequence, so `A6` routes it in code and uses a model only to route chat messages |
| A code sandbox for the model to run its own scripts over tool results | Totals come from server endpoints today; add it only if the chat needs calculations those cannot answer |

---

## 7. Order of work

| Step | Outcome | Estimate |
|---|---|---|
| A0 | Running locally, suites passing | 2–3 days |
| A1 | Baseline numbers | 3–4 days |
| A2 | Second account works | 2–3 days |
| A3 | Cheaper, safer prompts | 1.5 weeks |
| A4 | Evaluation set, runner, CI | 1 week (overlaps A3) |
| A5 | Resume import, answer bank, chat, memory | 3 weeks |
| A6 | Pipeline graph, approval interrupts, MCP servers | 3 weeks |
| B | Server for invited users | 2–3 weeks |

About 12–14 weeks in total for one or two developers. `A5` and `A6` can run side by side with two
developers; the chat router (`AG-06`) needs the chat from `FE-03`.
