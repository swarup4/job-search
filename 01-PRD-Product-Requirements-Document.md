# Product Requirements Document (PRD)

| | |
|---|---|
| **Product** | JobPilot — Agentic AI Job Search Platform |
| **Owner** | Swarup Saha |
| **Status** | Draft v1.0 |
| **Scope** | Personal, single-user tool |

---

## 1. Overview / Vision

JobPilot is a personal job-search co-pilot built from a set of specialized AI agents that work together to discover relevant job openings, analyze how well they match your profile, tailor your resume per job description, and manage the application pipeline — replacing the manual workflow you currently run by hand across job boards, ATS scoring, and spreadsheet tracking.

The system runs entirely on infrastructure you control: local/self-hosted LLMs, a local + Atlas-free-tier MongoDB split, and a Chrome extension for the one step that benefits from running inside your real browser session. No third-party AI vendor (including Claude) is used at runtime.

## 2. Problem Statement

Manually job hunting at the volume needed to land a Technical Lead / Senior Full-Stack / GenAI Engineer role involves repetitive, time-consuming work:

- Searching multiple sources daily for relevant openings
- Reading each JD and judging fit against your actual resume
- Manually tailoring resume content per role without over- or under-claiming skills
- Filling near-identical application forms across different ATS platforms
- Tracking status and remembering to follow up

This is slow, error-prone (easy to lose track of what was tailored/sent where), and doesn't scale to the volume of applications needed for a competitive search.

## 3. Goals & Objectives

- Cut the time from "job posted" to "tailored resume ready" to under 5 minutes
- Increase the number of well-matched applications submitted per week versus manual baseline
- Ensure every tailored resume reflects only skills you've explicitly confirmed — never fabricated
- Keep a single source of truth for application status and follow-ups
- Keep the whole system private and local — no resume/PII data sent to third-party cloud AI providers

## 4. Target User

Single persona: **Swarup Saha** — the sole user of this tool. No multi-tenant, no user accounts, no permissions system. Every requirement in this document and its companion documents is written for a single-user context.

## 5. Scope

### 5.1 In Scope (v1)
- Automated job discovery across Google/SerpAPI, Indeed (via MCP), LinkedIn, Naukri
- JD keyword extraction and Present/Missing skill-gap analysis against your resume
- Interactive keyword selection (you choose what to incorporate — no silent fabrication)
- Resume tailoring producing a `.tex` source file (LaTeX), based on your existing template
- Semi-autonomous application form-filling via a Chrome extension, with mandatory human review before submit
- Application pipeline tracking (Applied → Viewed → Interview → Offer/Rejected) with follow-up reminders
- Local dashboard for reviewing shortlists, approving applications, and tracking pipeline status

### 5.2 Out of Scope (v1)
- PDF compilation of the tailored resume (deferred — `.tex` output only for now)
- Fully autonomous auto-submit without human review
- Multi-tenant support, user accounts, or sharing with other users
- Mobile app (desktop/local-machine use only)
- Cover letter generation (unless explicitly requested later)
- Salary negotiation or offer-comparison tooling

## 6. Key Features

| Feature | Description | Maps to |
|---|---|---|
| Job Discovery | Daily automated pull of new listings matching your target roles/locations | Job Discovery Agent |
| JD Keyword Match & Gap Analysis | Extracts technical keywords from JD, diffs against your resume, shows Present/Missing lists | JD Match/Score Agent |
| Interactive Keyword Selection | You pick which missing keywords to incorporate before tailoring | JD Match/Score Agent (UI step) |
| Resume Tailoring | Generates a tailored `.tex` resume file reflecting only your selections | Resume Tailor Agent |
| Application Autofill | Chrome extension fills known application fields in your real browser session; you review and click Submit | Application Agent |
| Pipeline Tracking | Status board + follow-up reminders, synced with your existing Google Sheet habit | Tracking & Follow-up Agent |
| Orchestration | Coordinates all agents, holds shared state, pauses for your approval at key gates | Orchestrator (LangGraph Supervisor) |

## 7. User Stories (high level)

- As the user, I want new matching jobs pulled in automatically each day so I don't have to search manually.
- As the user, I want to see which technical keywords a JD requires that my resume doesn't currently show, so I can decide what to add.
- As the user, I want to explicitly choose which keywords get incorporated into my tailored resume, so nothing gets fabricated on my behalf.
- As the user, I want a `.tex` file I can review/compile myself before it becomes my final resume.
- As the user, I want application forms mostly pre-filled when I open them, but I always want to review and click Submit myself.
- As the user, I want one place to see the status of every application and be reminded when a follow-up is due.

## 8. Success Metrics

- Time from job discovery to tailored `.tex` ready: **< 5 minutes**
- % of JD keyword gaps correctly identified (spot-checked against manual judgment)
- Applications submitted per week vs. manual baseline
- Zero instances of fabricated/unselected skills appearing in a tailored resume
- Interview conversion rate before vs. after adopting the tool

## 9. Assumptions & Constraints

- Runs on your own hardware (Mac + local GPU/CPU capacity for local LLM inference)
- Local LLM tool-calling reliability varies by model size — larger models required for high-stakes agents (Orchestrator, Resume Tailor)
- Vector search requires either MongoDB Atlas (free tier) or Docker-based local MongoDB with `mongot` (native macOS `mongot` doesn't exist) — current decision: Atlas free tier for vector data, local MongoDB for structural data
- Job board Terms of Service restrict automated submission — system is semi-autonomous by design, not fire-and-forget

## 10. Risks (product-level)

| Risk | Impact | Mitigation |
|---|---|---|
| Local model produces unreliable tool calls | Broken agent workflows | Test tool-calling accuracy per model before committing; use strongest available model for high-stakes agents |
| Resume tailoring drifts toward fabrication | Damaged credibility, ethical issue | Hard-coded guardrail: only user-selected keywords are incorporated |
| Job board detects/blocks automation | Account flags, CAPTCHA | Chrome extension approach (real session) instead of headless browser automation for applying |
| Atlas free tier storage limits exceeded | Vector search stops working | Keep only embedding-relevant data in Atlas; monitor 512MB cap |

---
*See companion documents: SRS, Architecture & System Design, UI/UX Wireframes & User Flows, Roadmap & Backlog.*
