# UI/UX Wireframes & User Flows

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | Draft v1.0 |

---

## 1. Design Principles

- **Minimal, not polished.** Single user, no per-user views, no permissions logic — functional clarity over visual design investment.
- **MVP surface: Streamlit/Gradio.** Fast to build, good enough for daily personal use. A full React frontend is an optional later upgrade, not a v1 requirement.
- **Every automated step ends at a human checkpoint.** Keyword selection and application review are non-negotiable pauses — the UI should make the pending-review queue impossible to miss.
- **Desktop only.** No mobile responsiveness required — this runs alongside your browser on your own machine.

---

## 2. Screen Inventory

1. **Dashboard / Pipeline Board** — home screen, shows all jobs by pipeline stage
2. **Job Shortlist / Match Review** — ranked list of newly discovered jobs with match scores
3. **Keyword Selection Screen** — Present/Missing keyword lists, checkbox selection
4. **Resume Tailor Preview** — shows the rendered `.tex` (or a readable diff) before finalizing
5. **Application Review Screen** (dashboard-side) — tracks staged applications awaiting submission
6. **Chrome Extension Popup** — inline, on the actual ATS page

---

## 3. Wireframes (text-based layout)

### 3.1 Dashboard / Pipeline Board

```
┌──────────────────────────────────────────────────────────────────────┐
│  JobPilot                                              [⟳ Refresh]    │
├──────────────────────────────────────────────────────────────────────┤
│  New (12)      Reviewed (5)     Tailored (3)    Applied (8)  Interview│
│ ┌──────────┐  ┌──────────┐    ┌──────────┐    ┌──────────┐ (2)      │
│ │ Job Card │  │ Job Card │    │ Job Card │    │ Job Card │ ┌───────┐│
│ │ Company  │  │ Company  │    │ Company  │    │ Company  │ │ Job   ││
│ │ Match 82%│  │ Match 91%│    │ Match 78%│    │ Applied  │ │ Card  ││
│ └──────────┘  │ Match 66%│    └──────────┘    │ 3d ago   │ └───────┘│
│  ...          └──────────┘     ...            └──────────┘  ...      │
├──────────────────────────────────────────────────────────────────────┤
│  ⚠ Pending your review: 3 keyword selections · 1 application to submit│
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Job Shortlist / Match Review

```
┌──────────────────────────────────────────────────────────────────────┐
│  Today's Shortlist (12 new jobs)                    Sort: Match % ▾   │
├──────────────────────────────────────────────────────────────────────┤
│  ● Senior GenAI Engineer — Acme Corp            Match: 91%   [Review] │
│    Bengaluru · Posted 2h ago · Source: LinkedIn                       │
│  ● Technical Lead — Full Stack — BetaSoft       Match: 84%   [Review] │
│    Remote (India) · Posted 5h ago · Source: Indeed                    │
│  ● Staff Engineer — GammaTech                   Match: 61%   [Review] │
│    Bengaluru · Posted 1d ago · Source: Google Search                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Keyword Selection Screen (core interactive step)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Senior GenAI Engineer — Acme Corp                    Match: 91%      │
├──────────────────────────────────────────────────────────────────────┤
│  ✓ Present in your resume            │  ○ Missing — select to add     │
│  ─────────────────────────           │  ─────────────────────────    │
│  ✓ LangGraph                          │  ☐ Ragas                      │
│  ✓ Azure OpenAI                       │  ☐ AWS Bedrock                │
│  ✓ FastAPI                            │  ☐ Kubernetes  ⚠ not in profile│
│  ✓ MongoDB                            │  ☐ Terraform                  │
│  ✓ React / TypeScript                 │                               │
├──────────────────────────────────────────────────────────────────────┤
│  ⚠ Risk flag: JD asks for 5+ yrs Kubernetes — not reflected anywhere  │
│                                                                          │
│                       [ Skip this job ]   [ Tailor Resume → ]          │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 Resume Tailor Preview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Tailored .tex Preview — Acme Corp (v1)                                │
├──────────────────────────────────────────────────────────────────────┤
│  Skills section diff:                                                  │
│    + Ragas          (added — you selected this)                        │
│    + AWS Bedrock     (added — you selected this)                       │
│    (all other sections unchanged from base template)                   │
├──────────────────────────────────────────────────────────────────────┤
│  [ View full .tex ]     [ Open in editor ]     [ Confirm & Stage ]     │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.5 Application Review Screen

```
┌──────────────────────────────────────────────────────────────────────┐
│  Staged Applications — Awaiting Your Submission (1)                    │
├──────────────────────────────────────────────────────────────────────┤
│  Senior GenAI Engineer — Acme Corp                                     │
│  .tex ready · Q&A answers prepared · Not yet opened in browser         │
│                                          [ Open Application Page → ]   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.6 Chrome Extension Popup (on the ATS page)

```
┌───────────────────────────────┐
│  JobPilot Autofill              │
├───────────────────────────────┤
│  Job: Senior GenAI Engineer      │
│  Company: Acme Corp               │
├───────────────────────────────┤
│  ✓ 6 fields auto-filled           │
│  ⚠ 2 fields need your input        │
│  📎 Resume: acme_v1.tex            │
│     [Copy file path]                │
├───────────────────────────────┤
│  Review the highlighted fields    │
│  on the page, then submit          │
│  yourself when ready.               │
└───────────────────────────────┘
```

---

## 4. User Flows

### 4.1 Daily Discovery → Review Flow
```
1. Scheduled discovery run completes (background, no user action)
2. User opens Dashboard → sees "New (N)" column populated
3. User clicks a job card → Job Shortlist detail view
4. User clicks [Review] → JD Match Agent runs → Keyword Selection screen appears
```

### 4.2 Keyword Selection → Tailoring Flow
```
1. User reviews Present/Missing lists on Keyword Selection screen
2. User checks boxes for keywords to incorporate (or none, if no gaps to address)
3. User clicks [Tailor Resume →]
4. System renders .tex → Resume Tailor Preview screen shown
5. User reviews diff → clicks [Confirm & Stage]
6. Job moves to "Tailored" column on Dashboard
```

### 4.3 Apply Flow
```
1. User clicks a "Tailored" job card → Application Review Screen
2. User clicks [Open Application Page →] → ATS site opens in Chrome
3. Extension popup auto-appears with job context
4. Extension fills known fields, highlights them on the page
5. User reviews highlighted fields, fills any flagged gaps manually
6. User copies resume file path, attaches via native file picker (2 clicks)
7. User reviews the full form themselves
8. User clicks Submit on the ATS page itself (not in the extension)
9. Extension detects the submit action (or user marks it manually in the popup)
10. Dashboard updates: job moves to "Applied" column
```

### 4.4 Tracking & Follow-up Flow
```
1. Tracking Agent monitors applications collection for status age
2. When a follow-up interval is reached, a draft email appears in the
   "Pending your review" banner on the Dashboard
3. User reviews/edits draft, sends manually (or via configured email tool)
4. Status/event logged; Google Sheet synced automatically
```

---

## 5. Interaction Notes

- The **"Pending your review" banner** on the Dashboard (Section 3.1) is the single most important UI element — it's the visible surface for every human-approval gate in the system (keyword selections, staged applications, due follow-ups). Nothing should require the user to hunt for what needs attention.
- No notification/alert system needed beyond this banner, given single-user daily-check usage.
- Risk flags (e.g., seniority mismatches) are shown inline at the point of decision (Keyword Selection screen), not buried in a separate report.
