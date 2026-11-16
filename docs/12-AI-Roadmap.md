# 12 — AI Roadmap

| | |
|---|---|
| **Written** | 2026-11-16 |
| **Replaces** | Steps `A3`–`A6` of [doc 10](10-Context-Engineering-Launch-Plan.md). Its gap analysis, Stage B (server) and decisions D1–D4 still stand |
| **Covers** | Roadmap Phases 7, 8 and 10 in [05-Roadmap-Backlog.md](../05-Roadmap-Backlog.md), plus the AI half of Phase 9 |
| **Also reviewed** | [ai-job-search-dev/ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) at `745e677`, for ideas worth borrowing (§3) |

One goal: **every model call fits a fixed budget, and no step makes a call larger.** Six steps,
done in order. Each has one outcome and one check.

Task ids from doc 10 are kept where the task is the same. New ones are `CE-11` to `CE-13`,
`EV-06` and `QA-01`.

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
| Candidate block (skill inventory and profile digest) | 3,000 | not limited |
| Posting text, after cleaning | 3,000 | cut at 4,000 (5,333 for a captured page), uncleaned |
| Tool definitions in any call | 1,600 (10%) | no call has tools yet |
| One tool result | 1,000, paged beyond that | — |

---

## 2. Where things stand

Done and merged (PR #58): usage log per call with cached tokens, per-user indexes, per-profile
inventory lock, retry budget, a version on every prompt.

Already right, and kept: the scoring call compares against the stored brief, not the full
posting; word-for-word matches are decided in code; scores are counted, not generated; quotes are
checked against their source.

Not started: everything below. Step 1 is blocked on the Atlas cluster, Voyage key and model
choice (doc 10, `LS-02`–`LS-04`).

---

## 3. What the reference repository does well

It is a Claude Code workspace for one person: slash commands, three subagents and Python tools
over files on disk. Its command files are large (the apply command alone is about 11,000 tokens)
because it assumes a 200,000-token hosted model. JobPilot cannot copy its prompts into a
16,384-token window. Its habits for keeping data out of the conversation are worth taking.

| What it does | Where it lands here |
|---|---|
| A deterministic gate (`posting_guard.py`) strips hidden HTML and invisible characters and quotes instruction-shaped lines before any model reads a posting | `CE-11`, step 2 |
| State is queried, not read: a tool returns a few compact rows from the job list, and results are written back by a tool, so the list never enters the conversation | Rule 5; `MC-01` in step 6 |
| A compact rubric is built from the profile once and passed inline to each scoring worker; workers never re-read the profile | Rule 2; `CE-13` in step 3 |
| Location and language are pass/fail gates checked before any scoring | `CE-12`, step 2 |
| A run scores a fixed number of postings; the rest are deferred to the next run, not dropped | `CE-07`, step 2 |
| Cheap triage for every posting, expensive depth only for the one being applied to | Already the shape here: brief and compare for all, tailoring on request |
| Workers that hold untrusted posting text have no write tools; edits come back as structured changes for the caller to apply | Step 5 chat and step 6 tools |
| The compiled PDF is checked in code: page count and the text a tracking system would extract | `QA-01`, step 5 |
| Verification runs once, at the end; nothing already in context is read again | Rule 2 |
| Recorded outcomes feed back into how fit is judged | `FE-04`, step 5 |

Not taken: scores written by the model against a rubric (JobPilot counts coverage in code, which
is cheaper and repeatable), portal scrapers for LinkedIn, and a second model that reviews every
draft (the code checks here do that job without a call).

---

## 4. The road

### Step 1 — Measure (3–4 days, blocked on setup)

- [ ] `EV-00` Score about 50 real Indian postings against one profile. Save the per-step summary
  from `GET /api/llm-usage/summary`.
- [ ] `EV-02` Label 20 of those postings and 3 profiles: requirements, the four details,
  present/missing verdicts. Grow the set later; 20 is enough to catch a regression.

**Check:** a saved table of tokens, calls, retries and time per step.

### Step 2 — Send less (about 1 week)

- [ ] `CE-04` **Clean postings.** New `ai/agents/cleaning.py`: links become their text, images
  go, blank and repeated lines collapse. If the text is still over budget, keep sections by
  heading (responsibilities, requirements, qualifications, skills) and drop benefits and legal
  text. The evidence checks run on the same cleaned text.
- [ ] `CE-11` **Guard postings.** In the same module: remove zero-width and other invisible
  characters, and hidden elements where the source is HTML. Lines addressed to an AI are kept
  but recorded on the posting, so the user can be shown that a posting tried it.
- [ ] `CE-03` **Read each posting once.** The brief also carries experience, salary and job type,
  so the separate details call goes. For captured pages the parse call returns the brief fields.
- [ ] `CE-12` **Gates before the model.** Location, work mode and minimum years are compared in
  code against the user's preferences as soon as the brief exists. A posting that fails is marked
  with the reason and is not sent to the compare call.
- [ ] `CE-07` **Score only relevant postings, in capped runs.** Filter by the user's saved roles
  and locations; score a fixed number per run and leave the rest for the next one.
- [ ] `CE-06` Remove the posting embedding that nothing reads.
- [ ] `CE-09` Send all near-miss label vectors in one search request.

**Check:** model calls per posting drop from four to at most three; prompt tokens per posting
drop by at least a third; accuracy on the labelled set does not fall.

### Step 3 — Arrange for reuse (3–4 days)

- [ ] `CE-13` **One candidate block.** Skill inventory and profile digest are rendered once per
  profile version into a single block, identical byte for byte on every call, and stored. Every
  prompt that needs the candidate uses this block and nothing else from the profile.
- [ ] `CE-01` **Reorder the scoring prompt:** system, candidate block, job, then the requirements
  to judge, each in its own tag. `COMPARE_SYSTEM` names each tag and says which is the question.
- [ ] `CE-02` **Same order and tags for tailoring**, with the untrusted-input rule.

**Check:** from the second posting of a run, cached tokens are above zero where the model server
reports them; a new test with a hostile requirement label passes.

### Step 4 — Lock it in (about 1 week)

- [ ] `EV-03` **Runner** in `ai/eval/`: requirement precision and recall, verdict accuracy, the
  rate of wrong "present" verdicts, tokens and time per posting, per prompt version and model.
- [ ] `EV-06` **Budget tests.** One test per prompt builds its largest realistic input and fails
  if any row of the budget table is exceeded.
- [ ] `EV-04` One live adversarial test per prompt.
- [ ] `EV-05` CI: lint, both suites and the budget tests on every push.
- [ ] `CE-10` Try embedding each chunk with its role and company in front. Keep it only if the
  labelled set shows related and unrelated scores further apart.

**Check:** a prompt or model change produces a before-and-after report, and an oversized prompt
fails the build.

### Step 5 — Features, on the same contract (about 3 weeks)

- [ ] `FE-01` **Resume import.** PDF or DOCX to markdown, one schema-constrained call per section,
  each value checked against the document, shown for confirmation before saving.
- [ ] `FE-02` **Answer bank.** Save answers typed in the extension. For a question the word match
  misses, search the bank by embedding with a threshold and give the model only the question and
  the matches. It returns the key of a stored answer or "ask the user", never a new fact.
- [ ] `FE-03` **Resume chat**, with a fixed layout and a limit on every part:

  | Order | Part | Limit (tokens) | Changes |
  |---|---|---|---|
  | 1 | System: role, rules, guide to the tags | 500 | never |
  | 2 | Candidate block and the user's learned rules | 3,000 | when the profile changes |
  | 3 | Summary of earlier turns | 600 | when the recent turns overflow |
  | 4 | Recent turns, word for word | 2,000 | each turn |
  | 5 | Retrieved chunks and the resume section being edited | 1,500 | each turn |
  | 6 | The user's message | 500 | each turn |
  | | Reply, plus the retry reserve | 2,150 | |

  That is 10,250 of 16,384. When part 4 passes its limit, the oldest turns are folded into part 3
  as a record of decisions, constraints and open items. The model returns edits as structured
  changes; code checks them for invented words; the user accepts or rejects each. No tools.
- [ ] `FE-04` **Memory**, two stores only. *Learned rules*: a short keyed list updated in place,
  shown and editable in Settings, capped so it always fits part 2. *Events*: an append-only log
  of tailor, apply and status changes, retrieved by relevance into part 5. Both are built from
  the raw turns, never from a summary.
- [ ] `QA-01` **Check the compiled PDF in code:** page count, and that the extracted text contains
  the contact details and every keyword the user selected.

**Check:** a new tester goes from an uploaded resume to a tailored PDF without typing a profile;
the chat stays inside its budget over a 40-turn conversation.

### Step 6 — Graph and tools (about 2 weeks)

LangGraph and MCP stay in (decision D4), kept small.

- [ ] `AG-01` **Pipeline graph.** The existing functions become nodes with fixed edges and
  unchanged prompts. State holds ids and structured results, never a message list.
- [ ] `AG-02` **Checkpoints in MongoDB**, so a run survives a restart. Replaces the in-memory run
  slots.
- [ ] `AG-03` **Two approval interrupts:** keyword selection after scoring, and confirmation
  before an application is marked applied. The server's own checks stay.
- [ ] `AG-06` **Chat router.** One small call sorts a message into: question about my data,
  change my resume, do something (score, tailor, find jobs), or small talk. Small talk gets no
  retrieval and no tools.
- [ ] `MC-01` **`jobpilot_api` as an MCP server**, read-only, about seven task-shaped tools
  (`job_search`, `job_get`, `match_get`, `resume_get`, `application_list`, `profile_get`,
  `status_get`). Lists are paged and return only the columns asked for. Totals come from the
  server, not from the model adding rows.
- [ ] `MC-02` **`latex` MCP server:** render and compile. A failed compile returns the first
  error line only.
- [ ] `MC-05` **Tool allow-list per node.** The model sees only the tools for the route it is on,
  and only the chat's "question about my data" route has any. `EV-06` covers the tool budgets.

**Check:** the pipeline runs as a graph with both interrupts and survives a restart; tokens per
posting are no higher than after step 3; the chat picks the right tool on the labelled set.

---

## 5. Left out, and why

| Item | Why |
|---|---|
| Discovery sources as MCP servers (`P7-03`–`P7-05`) | The model never chooses a discovery tool; code calls the scrapers directly. Wrapping them adds tool definitions and no ability. Revisit if another client needs them |
| A follow-up drafting agent (`P8-04`) | Needs the events log from `FE-04` and real usage first. Phase 11 |
| A model-driven supervisor for the pipeline | The pipeline is a fixed sequence. Only the chat needs a model to route |
| A second model reviewing each draft | Code already checks for invented words and missing keywords, at no token cost |
| Ragas, Langfuse or Phoenix (`P10-01`, `P10-07`) | The usage log and the runner in step 4 answer the same questions for this release. Add a tracing tool when there are more users than one team can read logs for |

---

## 6. Order

| Step | Outcome | Estimate |
|---|---|---|
| 1 | Baseline numbers and a labelled set | 3–4 days |
| 2 | Fewer and smaller calls | 1 week |
| 3 | Prompts ordered for reuse | 3–4 days |
| 4 | Budgets and accuracy enforced in CI | 1 week |
| 5 | Import, answer bank, chat, memory | 3 weeks |
| 6 | Graph, approvals, two MCP servers | 2 weeks |

About 8 weeks for one or two developers. Steps 5 and 6 can run side by side, except the chat
router, which needs the chat.
