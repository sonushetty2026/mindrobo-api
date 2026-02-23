# TASKBOARD — Phase 2 Sprint

## 🎯 Goal: All 9 features complete = ready for first 5 paying customers

## Priority Order & Assignments

| # | Issue | Title | Agent | Status |
|---|-------|-------|-------|--------|
| 1 | #58 | Marketing Website + Auth | Frontend + Backend | ✅ MERGED (PR #67 + #68) |
| 2 | #59 | Agent Personality Builder | Frontend + Backend | ✅ Frontend PR #69 ready | Backend pending |
| 3 | #60 | Availability Scheduler + Booking | Backend + Frontend | ✅ Frontend PR #72 | Backend PR #71 |
| 4 | #61 | Phone Number Setup (Twilio) | Backend + Frontend | ✅ Frontend PR #72 ready | Backend pending |
| 5 | #62 | Call Forwarding / Ring Timeout | Backend + Frontend | ✅ Frontend PR #72 ready | Backend pending |
| 6 | #63 | Call Recordings (Azure Blob) | Backend + Frontend | 🔲 WAVE 3 |
| 7 | #64 | Lead Capture Storage | Backend + Frontend | 🔲 WAVE 4 |
| 8 | #65 | Email Notifications (SendGrid) | Backend | 🔲 WAVE 4 |
| 9 | #66 | Subscription Management | Backend + Frontend | 🔲 WAVE 4 |

## Parallel Track
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #30 | QA: Test coverage 80%+ | QA | 🔄 IN PROGRESS (51% → 80%) |

## Completed
- ✅ #58 Marketing Website + Auth (PR #67 + #68 merged, QA verified)
- ✅ #29 War Room Dashboard (Phase 1, PR #54 merged)
- ✅ #32 Golden Path E2E Test (Phase 1, verified)

## Rules
- No feature is "done" until QA has clicked through it in a real browser
- Every PR includes QA Browser Flow Checklist
- QA: max 30k tokens/session, one module per session
- All agents: max 40k tokens, fresh session after 10 turns
- All worker agents on Sonnet. Orchestrator on Opus.
