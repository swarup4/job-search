# 12 — AI Roadmap

| | |
|---|---|
| **Written** | 2026-11-16, revised the same day for three decisions (see Decisions below) |
| **Replaces** | Steps `A3`–`A6` of [doc 10](10-Context-Engineering-Launch-Plan.md). Its gap analysis and Stage B (server) still stand |
| **Covers** | Roadmap Phases 6, 7, 8 and 10 in [05-Roadmap-Backlog.md](../05-Roadmap-Backlog.md), plus the AI half of Phase 9 |
| **Also reviewed** | [ai-job-search-dev/ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) at `745e677`, for ideas worth borrowing (§3) |

One goal: **every model call fits a fixed budget, and no step makes a call larger.** A setup
step, then six steps in order. Each has one outcome and one check.

Task ids from doc 10 are kept where the task is the same. New ones are `OS-01` to `OS-08`,
`CE-11` to `CE-13`, `EV-06`, `EV-07`, `FE-05` and `QA-01`.

## Progress

*Updated 2026-11-16. On branch `ai-roadmap-docs`, PR #62.*

Steps 2 and 3 are built, and the parts of step 4 that need no model. **None of it has
been measured**, so the checks that compare against a baseline are open. The stack also
changes in step 0, so the first baseline will be taken on the current code with the new
stack. A before-number for steps 2 and 3 would need step 0 applied on top of commit
`7504b03`, the last one before these changes; without that, those two steps are judged on
accuracy alone.

| Step | State | What is true |
|---|---|---|
| 0 Open-source stack | not started | Added 2026-11-16. Nothing in it waits on an outside account. It starts with `OS-07`: a local MongoDB and two models pulled into Ollama, which only the machine's owner can install |
| 1 Measure | waiting on step 0 | Needs nothing more than step 0 leaves behind |
| 2 Send less | built, not measured | All seven tasks. Model calls per scraped posting go from four to two (brief, compare), and to one more for a captured page (parse, which now returns the brief). Token and accuracy checks need step 1 |
| 3 Arrange for reuse | built, not measured | All three tasks. The hostile-label test passes. Cached tokens can only be seen on a real model server |
| 4 Lock it in | partly | `EV-06` budget tests and `EV-03` runner built and tested with the model faked. `EV-05` workflow written, never run. `EV-04` tests written, never run: no usable local model on this machine. `EV-07` and `CE-10` need the labelled set |
| 5, 6 | not started | |

**Tests**, run again on 2026-11-16 after the plan changed. AI tier: 337 pass, 1 fails — the
failure is the old one, `ai/.env.example` naming a hosted endpoint, which `OS-04` fixes. Seven
live-model tests are collected and not run. Lint passes in both tiers. **The server suite has
never been run** (no MongoDB here), so these are unverified: `test_multi_account.py` and
`test_llm_usage.py` from PR #58, `test_scoring_inputs.py`, and the database half of
`test_experience.py`. `OS-07` is where they first run.

**What the three decisions do to work already built.** Nothing built in steps 2 to 4 has to be
undone. Three pieces are touched again by step 0:

| Built | Touched by | How |
|---|---|---|
| `POST /resume-chunk/search-many` (`CE-09`) | `OS-01` | Keeps its shape; the searches behind it become one pass over the user's chunks |
| The two tool budgets in `config/llm.py` and their test (`EV-06`) | D5 | Stay pinned and unused until the chat returns |
| The evaluation runner (`EV-03`) | `EV-07` | It does not measure near misses, which `OS-05` and `CE-10` both need |

**Decisions made while building, to confirm:**

- *Minimum experience gate (`CE-12`).* "Min experience" in Search targets is read as
  the level you are looking for: a posting that states a minimum **below** it fails.
- *Work mode gate.* A posting that states a mode different from the saved one fails,
  including a remote posting when you saved hybrid.
- *Skill-only postings (`CE-07`).* A scoring run matches a saved skill against
  `techStack`. A posting kept by discovery only for a skill in its description, and
  not yet analyzed, is not picked up by a scoring run until Analyze reads it.
- *Captured pages (`CE-03`).* The parse call now returns the brief as well. Doc 10
  said to keep the two apart if the larger schema lowers accuracy on captured pages;
  that is unmeasured. `PARSE_VERSION` is 2, so the usage log separates old from new.
- *Tailoring (`CE-02`).* It is tagged and ordered, but does not use the candidate
  block: it needs the current role's bullets word for word, which the block does not
  hold.

## Decisions on 2026-11-16

| # | Decision | Effect on this plan |
|---|---|---|
| D5 | **No chat for now** | The resume chat, its router, the tools a model would choose from, and reranking are parked (§5). Nothing else depended on them |
| D6 | **Open source only**, because this is a community project | The hosted model router and the Voyage API go. Generation and embeddings both run on Ollama with open-weights models. This also settles `LS-03` in doc 10: the model is local |
| D7 | **No Atlas cluster** | Vector search moves into the server's own code as an exact cosine search, so any MongoDB works |

Five things for the owner to decide. Only the first blocks anything, and only `OS-04`:

- **Which generation model.** The code default is `qwen3.5:9b`; only `phi3` is pulled on the
  test machine, which is too small. The model must be open-weights under a licence D6 accepts,
  must honour a strict JSON schema, and must fit the memory of the machine it runs on. Every
  score and every baseline is tied to this choice.
- **MongoDB's licence.** The Community Server is under the SSPL, which is source-available but
  not approved by the Open Source Initiative. Staying on it is the practical choice. A strict
  reading of D6 would mean moving the server's data layer to PostgreSQL, which is a rewrite.
- **The repository has no `LICENSE` file.** A community project needs one before others can use
  or contribute to the code (`OS-06`).
- **Personal data in the repository.** `server/seed_profile.json`, `templates/base_resume.tex`
  and two files under `templates/GPT Template/` hold a real person's contact details, and six
  template files are named after him. Doc 10 left their removal to Stage B (`SV-12`). A
  community project is read by strangers sooner than that, so it may belong in step 0.
- **Whether the `latex` MCP server (`MC-02`) is still wanted.** With the chat parked, no model
  chooses a tool. §6 leaves the discovery servers out for exactly that reason, and the same
  reasoning applies here: a plain function does the same job.

The data already in the Atlas cluster (about 419 jobs) is not needed for any step here. A local
database starts empty and is filled by a discovery run.

---

## 1. The contract for the context window

These six rules apply to every prompt, existing and new. A change that breaks one is not merged.

| # | Rule | Why |
|---|---|---|
| 1 | **Code decides what it can; the model sees only what is left.** Exact matches, counts, filters, totals and routing of fixed sequences stay in code | A decision made in code costs no tokens and cannot be wrong in a new way |
| 2 | **Read once, store, reuse.** A posting is read by the model once and becomes a brief. A profile is read once and becomes the candidate block. Later calls use those, never the raw text | The largest inputs are paid for once, not per call |
| 3 | **Stable first, changing last.** Order in every prompt: system, candidate block, per-job data, the question | The model server can reuse the shared start of the prompt between calls |
| 4 | **Clean before the model reads.** Text from outside is cleaned and checked in code first, then fenced in a tag | Noise is not paid for, and hidden text never reaches the model |
| 5 | **State stays out of the prompt.** Lists, history and run state live in the database. A call receives ids and the few rows it needs | A prompt that carries state grows on every turn |
| 6 | **Every call has a budget and is measured against it.** A test fails when a call exceeds its budget | Growth is caught in review, not in production |

### Budgets

The window is 16,384 tokens. `check_budget` already enforces the first three rows; the rest are
new limits, enforced by `EV-06`. They are starting values: step 1 replaces them with measured ones.

| Part | Limit (tokens) | Today |
|---|---|---|
| System prompt | 2,457 (15% of the window) | 237–533 across the six prompts |
| All input | 9,830 (60%) | enforced |
| Reserved for a retry | 650 | enforced |
| Candidate block (skill inventory and profile digest) | 3,000 | enforced: `inventory.render_candidate` |
| Posting text, after cleaning | 3,000 | enforced: `cleaning.clean_posting` |
| Tool definitions in any call | 1,600 (10%) | parked with the chat (§5): no call has tools. Limit pinned in `config/llm.py` |
| One tool result | 1,000, paged beyond that | parked with the chat |

---

## 2. Where things stand

Done and merged (PR #58): usage log per call with cached tokens, per-user indexes, per-profile
inventory lock, retry budget, a version on every prompt.

Already right, and kept: the scoring call compares against the stored brief, not the full
posting; word-for-word matches are decided in code; scores are counted, not generated; quotes are
checked against their source.

Built since: steps 2 and 3 and part of step 4 (see Progress). Nothing waits on
an outside account any more. Step 0 can start once the owner says to build it.

**What step 0 changes in the product roadmap.** [05-Roadmap-Backlog.md](../05-Roadmap-Backlog.md)
is the owner's document and is not edited here. These of its tasks are marked done there and are
replaced by step 0:

| Roadmap task | What it built | After step 0 |
|---|---|---|
| `P5-06`, `P6-04` | Voyage `voyage-4-lite` embeddings; `NEAR_MISS_THRESHOLD` 0.35 measured on them | Ollama embeddings (`OS-02`); threshold measured again (`OS-05`) |
| `P5-11`, and the Phase 5 decision "one hosted path" | The hosted router as the only model | A local model on Ollama (`OS-04`). The roadmap's note that NFR-3 and invariant 3 are now false no longer applies: generation is local again |
| `P5-12`, `P6-06` | `$vectorSearch` indexes on `job_descriptions` and `resume_chunks` | Removed (`OS-01`). Deviation 6, "one store, Atlas", becomes "one store, any MongoDB" |
| `P6-05` | Two-stage retrieval with a Voyage reranker | Removed (`OS-03`); parked with the chat |

---

## 3. What the reference repository does well

It is a Claude Code workspace for one person: slash commands, three subagents and Python tools
over files on disk. Its command files are large (the apply command alone is about 11,000 tokens)
because it assumes a 200,000-token hosted model. JobPilot cannot copy its prompts into a
16,384-token window. Its habits for keeping data out of the conversation are worth taking.

| What it does | Where it lands here |
|---|---|
| A deterministic gate (`posting_guard.py`) strips hidden HTML and invisible characters and quotes instruction-shaped lines before any model reads a posting | `CE-11`, step 2 |
| State is queried, not read: a tool returns a few compact rows from the job list, and results are written back by a tool, so the list never enters the conversation | Rule 5 |
| A compact rubric is built from the profile once and passed inline to each scoring worker; workers never re-read the profile | Rule 2; `CE-13` in step 3 |
| Location and language are pass/fail gates checked before any scoring | `CE-12`, step 2 |
| A run scores a fixed number of postings; the rest are deferred to the next run, not dropped | `CE-07`, step 2 |
| Cheap triage for every posting, expensive depth only for the one being applied to | Already the shape here: brief and compare for all, tailoring on request |
| The compiled PDF is checked in code: page count and the text a tracking system would extract | `QA-01`, step 5 |
| Verification runs once, at the end; nothing already in context is read again | Rule 2 |
| Recorded outcomes feed back into how fit is judged | `FE-04`, step 5 |

Not taken: scores written by the model against a rubric (JobPilot counts coverage in code, which
is cheaper and repeatable), portal scrapers for LinkedIn, and a second model that reviews every
draft (the code checks here do that job without a call).

---

## 4. The road

### Step 0 — Open-source stack (about 1 week)

Done before measuring, because a baseline is only useful on the stack that will be kept. The
tasks are listed in the order to do them, which is not the order of their ids.

- [ ] `OS-07` **Set up the machine, and run the server suite for the first time.** Install
  MongoDB Community Server on `127.0.0.1:27017`. Pull `bge-m3` and the chosen generation model
  into Ollama. Then run `uv run --frozen pytest -q` in `server/` and fix what fails: four test
  files have never run (`test_multi_account.py`, `test_llm_usage.py`, `test_scoring_inputs.py`,
  and the database half of `test_experience.py`). Everything after this is tested on that
  database. *Needs the owner of the machine: an earlier attempt to run a downloaded `mongod`
  was blocked by the permission settings.*
- [ ] `OS-01` **Exact vector search in the server.** `resume_chunk.service.search` loads the
  user's embedded chunks with an ordinary query and ranks them by cosine similarity in Python. A
  profile is a few dozen chunks, so this is exact and fast, and needs no new dependency.
  `search_many` loads the chunks once for all vectors. Remove `_ensure_vector_index` and both
  of its calls from `config/database.py` (the `job_descriptions` index as well as the
  `resume_chunks` one) and the score rescaling in `cosine_from_score`. Point `MONGODB_URI` in
  `server/.env.example` at the local database: it still carries an Atlas hostname. Add the
  tests the Atlas version could never have: ordering, the per-user filter, chunks with no
  vector.
- [ ] `OS-02` **Embeddings from Ollama.** Replace the Voyage client in `ai/rag/embeddings.py`
  with a call to Ollama's OpenAI-compatible embeddings endpoint, using the HTTP client already in
  the project. Start with `bge-m3`: it returns 1,024-dimension vectors, the size the database
  already stores, so there is no schema change. Confirm the licence of the model pulled. Remove
  the `voyageai` dependency. Voyage is also named in `rag/indexing.py`, `rag/retrieval.py`,
  `agents/matching.py`, `api/settings/router.py` (which reports the embedding model to the
  Settings screen), `tests/test_embeddings.py`, `tests/test_retrieval.py`, and two guardrail
  tests: the one that limits who imports Voyage, and the one that keeps its key out of the
  server and the browser. Voyage embedded a query and a stored chunk differently; check whether
  the new model does, and keep one code path if it does not.
- [ ] `OS-03` **Remove reranking and two-stage retrieval** (`rag.retrieve`, `rag.rerank`). They
  have no caller without the chat. Keep `nearest_spans`, which scoring uses. The Settings
  endpoint and its "Models & privacy" panel also report a rerank model; remove that field.
- [ ] `OS-04` **Point `ai/.env.example` at Ollama** with the chosen generation model, and remove
  the Voyage settings. The guardrail test that forbids a hosted endpoint then passes, and the CI
  workflow can go green. *Waits on the owner's choice of generation model.*
- [ ] `OS-05` **Re-embed and re-measure.** Every stored chunk is embedded again with the new
  model. Today a re-index keeps a chunk's vector when its text is unchanged, so old vectors
  would survive a change of model: store the embedding model's name on each chunk, and treat a
  chunk embedded by a different model as having no vector. `NEAR_MISS_THRESHOLD` (0.35) was
  measured for Voyage's vectors and must be measured again: with the helper in
  `rag/embeddings.py` now, and on the labelled set after step 1 (`EV-07`).
- [ ] `OS-08` **Bring the setup documents in line.** Rewrite
  [doc 11](11-Local-Setup-Windows.md) for a local MongoDB and Ollama, with no Atlas cluster and
  no Voyage key. Correct the README where it says vector search needs Atlas. In doc 10, the
  paragraph "Next, and blocked on setup only you can do" still asks for an Atlas cluster and a
  Voyage key, and its pointer to these decisions names the wrong section.
- [ ] `OS-06` **Add a `LICENSE` file** once the owner has chosen one, and record the MongoDB
  licence decision in the README.

**Check:** both test suites pass against a local MongoDB with no network access; scoring a
posting with a missing requirement returns a near-miss hint; no API key and no hostname outside
this machine appears in any `.env` template; the CI workflow has run green once.

### Step 1 — Measure (3–4 days)

- [ ] `EV-00` Score about 50 real Indian postings against one profile. Save the per-step summary
  from `GET /api/llm-usage/summary`, with the model names and the machine it ran on.
- [ ] `EV-02` Label 20 of those postings and 3 profiles: requirements, the four details,
  present/missing verdicts, and true near misses. Grow the set later; 20 is enough to catch a regression.
  *Store it under `ai/eval/data/` in the shape `ai/eval/dataset.py` reads, and take personal
  details out of the profiles before committing. That shape has no field for near misses yet;
  `EV-07` adds it.*

**Check:** a saved table of tokens, calls, retries and time per step, and the budget table in §1
updated with measured numbers.

### Step 2 — Send less (about 1 week)

- [x] `CE-04` **Clean postings.** New `ai/agents/cleaning.py`: links become their text, images
  go, blank and repeated lines collapse. If the text is still over budget, keep sections by
  heading (responsibilities, requirements, qualifications, skills) and drop benefits and legal
  text. The evidence checks run on the same cleaned text.
- [x] `CE-11` **Guard postings.** In the same module: remove zero-width and other invisible
  characters, and hidden elements where the source is HTML. Lines addressed to an AI are kept
  but recorded on the posting, so the user can be shown that a posting tried it.
  *Recorded as `brief.flagged`. No screen shows it yet.*
- [x] `CE-03` **Read each posting once.** The brief also carries experience, salary and job type,
  so the separate details call goes. For captured pages the parse call returns the brief fields.
- [x] `CE-12` **Gates before the model.** Location, work mode and minimum years are compared in
  code against the user's preferences as soon as the brief exists. A posting that fails is marked
  with the reason and is not sent to the compare call.
  *`ai/agents/gates.py`. The match is stored with score 0, the reason as its one risk, and
  `gate` set. No screen treats a gated match differently yet.*
- [x] `CE-07` **Score only relevant postings, in capped runs.** Filter by the user's saved roles
  and locations; score a fixed number per run and leave the rest for the next one.
  *`GET /match/unscored?relevant=true`; `SCORING_MAX_JOBS`, default 50. The run reports
  `remaining`.*
- [x] `CE-06` Remove the posting embedding that nothing reads. *The step is gone; the
  server endpoint is left for the feature that will read it. Its Atlas index goes with `OS-01`.*
- [x] `CE-09` Send all near-miss label vectors in one search request.
  *`POST /resume-chunk/search-many`. `OS-01` turns the searches behind it into one pass.*

**Check:** model calls per posting drop from four to at most three; prompt tokens per posting
drop by at least a third; accuracy on the labelled set does not fall.

### Step 3 — Arrange for reuse (3–4 days)

- [x] `CE-13` **One candidate block.** Skill inventory and profile digest are rendered once per
  profile version into a single block, identical byte for byte on every call, and stored. Every
  prompt that needs the candidate uses this block and nothing else from the profile.
- [x] `CE-01` **Reorder the scoring prompt:** system, candidate block, job, then the requirements
  to judge, each in its own tag. `COMPARE_SYSTEM` names each tag and says which is the question.
- [x] `CE-02` **Same order and tags for tailoring**, with the untrusted-input rule.

**Check:** from the second posting of a run, cached tokens are above zero where Ollama
reports them, or time per call falls where it does not; a new test with a hostile requirement label passes.

### Step 4 — Lock it in (about 1 week)

- [x] `EV-03` **Runner** in `ai/eval/`: requirement precision and recall, verdict accuracy, the
  rate of wrong "present" verdicts, tokens and time per posting, per prompt version and model.
  *`python -m eval.runner --data … --out … [--baseline …]`. Tested with the model faked.
  `ai/eval/sample/` is one invented posting to show the label format; it is not `EV-02`.*
- [x] `EV-06` **Budget tests.** One test per prompt builds its largest realistic input and fails
  if any row of the budget table is exceeded. *`ai/tests/test_budgets.py`.*
- [ ] `EV-04` One live adversarial test per prompt. *Written in `ai/tests/test_live_llm.py`,
  seven tests. Not run: they need the generation model from `OS-07`. Run them with
  `pytest -m llm` and fix or record what fails.*
- [ ] `EV-05` CI: lint, both suites and the budget tests on every push.
  *`.github/workflows/ci.yml` written, never run. The AI job will fail until `OS-04`
  fixes the `ai/.env.example` guardrail failure. After `OS-01` the server job needs only a
  stock MongoDB container.*
- [ ] `EV-07` **Measure near misses in the runner.** Add a near-miss field to the labelled set
  and have the runner embed each missing requirement and the profile's chunks, then report
  how far apart the related and unrelated scores sit and what each threshold would flag. The
  runner needs no server for this, only the embedding model. `OS-05` and `CE-10` are both
  judged on this number, and the runner cannot produce it today.
- [ ] `CE-10` Try embedding each chunk with its role and company in front. Keep it only if
  `EV-07` shows related and unrelated scores further apart.

**Check:** a prompt or model change produces a before-and-after report, and an oversized prompt
fails the build.

### Step 5 — Features, on the same contract (about 2 weeks)

- [ ] `FE-01` **Resume import.** PDF or DOCX to markdown, one schema-constrained call per section,
  each value checked against the document, shown for confirmation before saving.
- [ ] `FE-02` **Answer bank.** Save answers typed in the extension. For a question the word match
  misses, search the bank by embedding with a threshold and give the model only the question and
  the matches. It returns the key of a stored answer or "ask the user", never a new fact.
  *The search reuses the exact cosine search from `OS-01`. Its threshold is a new one, question
  against question, and has to be measured: the near-miss threshold does not carry over.*
- [ ] `FE-04` **Learn from edits.** A short keyed list of rules per user, updated in place when
  the user accepts or declines a tailoring suggestion, shown and editable in Settings, and capped
  so it always fits in the tailoring prompt. *The cap is a new row in the budget table and a new
  case in `EV-06`. Adding rules to the prompt bumps `TAILOR_VERSION`.*
- [ ] `FE-05` **Show what step 2 built.** Two things are stored and shown nowhere: a match that
  failed a gate (`match.gate`, with the reason as its one risk) and the lines of a posting
  addressed to an AI (`brief.flagged`). A gated job should read as "outside your search
  targets", not as a 0% match, and should be listable apart from scored jobs. Agree the screens
  with the owner; this sits beside roadmap `P3-34`.
- [ ] `QA-01` **Check the compiled PDF in code:** page count, and that the extracted text contains
  the contact details and every keyword the user selected. *Only the base resume can be compiled
  today (`GET /resume/base/pdf`); a tailored resume has no PDF route, so that comes first. The
  library that extracts the text must be open source (D6).*

**Check:** a new tester goes from an uploaded resume to a tailored PDF without typing a profile.

### Step 6 — Graph (about 1.5 weeks)

LangGraph stays in (doc 10, decision D4), kept small.

- [ ] `AG-01` **Pipeline graph.** The existing functions become nodes with fixed edges and
  unchanged prompts. State holds ids and structured results, never a message list.
- [ ] `AG-02` **Checkpoints in MongoDB**, so a run survives a restart. Replaces the in-memory run
  slots. *Written through the API server, like every other write: the AI tier holds no database
  address, and a guardrail test fails if it opens a connection. So this is a small checkpointer
  over HTTP and a server module to store it, not LangGraph's own MongoDB checkpointer.*
- [ ] `AG-03` **Two approval interrupts:** keyword selection after scoring, and confirmation
  before an application is marked applied. The server's own checks stay. *The dashboard needs
  somewhere to show a waiting interrupt, which is roadmap `P8-08`.*
- [ ] `MC-02` **`latex` MCP server:** render and compile, called from the graph's code. A
  failed compile returns the first error line only. *Open question for the owner, in Decisions
  above: with no model choosing tools, a plain function does this job.*

**Check:** the pipeline runs as a graph with both interrupts and survives a restart; tokens per
posting are no higher than after step 3.

---

## 5. Parked with the chat

These return together when the chat does. The design is kept here so it is not lost.

| Task | What it is |
|---|---|
| `FE-03` Resume chat | A fixed prompt layout with a limit on every part: system 500, candidate block and learned rules 3,000, summary of earlier turns 600, recent turns 2,000, retrieved chunks and the section being edited 1,500, the message 500, reply and retry 2,150. That is 10,250 of 16,384 tokens. Older turns fold into the summary; edits come back as structured changes the user accepts or rejects |
| `AG-06` Chat router | One small call that sorts a message into a question, a resume change, an action, or small talk |
| `MC-01` `jobpilot_api` as an MCP server | About seven read-only, task-shaped tools with paged results. It has no purpose until a model chooses tools |
| `MC-05` Tool allow-list per node | With the two tool budgets in §1 |
| Reranking, and an events log for retrieval | Needed only for retrieval inside a conversation |

---

## 6. Left out, and why

| Item | Why |
|---|---|
| Hosted models and paid APIs of any kind | Decision D6 |
| Discovery sources as MCP servers (`P7-03`–`P7-05`) | The model never chooses a discovery tool; code calls the scrapers directly. Wrapping them adds tool definitions and no ability. Revisit if another client needs them |
| A follow-up drafting agent (`P8-04`) | Needs real usage first. Phase 11 |
| A model-driven supervisor for the pipeline | The pipeline is a fixed sequence |
| A second model reviewing each draft | Code already checks for invented words and missing keywords, at no token cost |
| Ragas, Langfuse or Phoenix (`P10-01`, `P10-07`) | The usage log and the runner in step 4 answer the same questions for this release. Both tools are open source, so they fit D6 if wanted later |

---

## 7. Order

| Step | Outcome | Estimate | State |
|---|---|---|---|
| 0 | Runs with no outside service | 1 week | not started; waits on a go-ahead, a local MongoDB and the model choice |
| 1 | Baseline numbers and a labelled set | 3–4 days | waiting on step 0 |
| 2 | Fewer and smaller calls | 1 week | built, not measured |
| 3 | Prompts ordered for reuse | 3–4 days | built, not measured |
| 4 | Budgets and accuracy enforced in CI | 1 week | partly built; `EV-04`, `EV-05`, `EV-07`, `CE-10` open |
| 5 | Import, answer bank, learning from edits, screens for gates | 2 weeks | not started |
| 6 | Graph, approvals, LaTeX server | 1.5 weeks | not started |

About 5 to 6 weeks of work remain for one or two developers.

**Open tasks, in order:** `OS-07`, `OS-01`, `OS-02`, `OS-03`, `OS-04`, `OS-05`, `OS-08`, `OS-06`;
`EV-00`, `EV-02`; `EV-04`, `EV-05`, `EV-07`, `CE-10`; `FE-01`, `FE-02`, `FE-04`, `FE-05`, `QA-01`;
`AG-01`, `AG-02`, `AG-03`, `MC-02`. That is 23 open and 12 done.

For Stage B (doc 10, section 5): a local model needs a server with enough memory, ideally a GPU.
Size it from the times recorded in step 1. Of `SV-12`, the part that corrected the "all
generation is local" wording is no longer needed, because the statement is now true. The rest of
it still stands: removing personal data from the repository, and correcting the README where it
describes a different system.
