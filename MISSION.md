# MindRobo Mission Brief — Orchestrator

## What MindRobo Is
MindRobo is an **AI receptionist for small businesses** (salons, clinics, restaurants, law firms, etc.).
When a customer calls, instead of voicemail or a busy signal, an AI agent answers, understands their request,
and takes action — books appointments, sends confirmations, answers questions using the business's knowledge base.

**Core stack**: Retell AI (voice), FastAPI (backend), PostgreSQL (data), Azure (cloud), Twilio (SMS).

---

## What's Already Built (DO NOT REBUILD THESE)
All of the following are DONE and merged to main. Agents must NOT rewrite them:
- ✅ Retell webhook receives call events → saves to `calls` table
- ✅ Twilio SMS — sends confirmation to caller + summary to business owner
- ✅ Business config table + CRUD endpoints (`/api/v1/businesses/`)
- ✅ WebSocket live dashboard (`/dashboard`)
- ✅ 14-test QA suite (pytest)
- ✅ systemd service (`mindrobo-api`)
- ✅ Self-serve onboarding flow at `/onboarding` (wizard — to be REPLACED by Issue #23)
- ✅ Website URL ingestion → knowledge base (`POST /api/v1/ingest/website`)

The live service runs at `http://localhost:8000`. Health: `curl http://localhost:8000/health`

---

## Open Issues — Your Sprint Backlog

### Priority 1 — Critical Path (do these first)
| # | Title | Agent |
|---|-------|-------|
| #23 | fix onboarding: URL/PDF ingest → review → publish (REPLACES current wizard) | ingestion + frontend |
| #17 | Deploy refactored code + re-run test call on live Retell number | backend |

### Priority 2 — Core Features
| # | Title | Agent |
|---|-------|-------|
| #20 | Voice excellence — natural, emotional voice tuning (Retell agent prompts) | backend |
| #16 | Twilio SMS approval flow (owner approves/rejects bookings by reply) | backend |
| #11 | WebSocket live dashboard improvements | frontend |
| #10 | Business config CRUD (already done — verify and close if complete) | qa |

### Priority 3 — Already Done — Close These
Issues #8, #9, #10, #12, #13, #14, #15, #18, #19 are likely DONE based on merged PRs.
Check each one: `gh issue view <N> -R sonushetty2026/mindrobo-api`
If the feature exists in the codebase, close it: `gh issue close <N> -R sonushetty2026/mindrobo-api`

---

## How to Assign Work to Agents

You communicate with agents by posting a GitHub Issue and adding the right label.
You can also directly instruct them by sending a message to their Telegram bot session if needed.

**Labels**: `backend`, `frontend`, `ingestion`, `qa`

### To assign an issue:
```bash
gh issue edit <N> -R sonushetty2026/mindrobo-api --add-label backend
gh issue comment <N> -R sonushetty2026/mindrobo-api --body "Please implement this. See PROJECT.md for workflow."
```

---

## Agent Capabilities Reference

| Agent | Bot | Model | Workspace | Branch |
|-------|-----|-------|-----------|--------|
| backend | @MindRobo_Backend_bot | Sonnet | ~/.openclaw/workspace/backend | worktree/backend |
| frontend | @MindRobo_Frontend_bot | Sonnet | ~/.openclaw/workspace/frontend | worktree/frontend |
| ingestion | @MindRobo_Ingestion_bot | Sonnet | ~/.openclaw/workspace/ingestion | worktree/ingestion |
| qa | @MindRobo_QA_bot | Sonnet | ~/.openclaw/workspace/qa | worktree/qa |

All agents have:
- Full filesystem read/write in their workspace
- `python3`, `pytest`, `alembic`, `curl`, `git`, `gh` CLI
- Ability to create commits, push branches, create PRs

---

## Decision Authority — What You Can Decide WITHOUT Asking the CEO

You (Orchestrator) and agents have FULL authority to:
- ✅ Write code, create files, run tests
- ✅ Create GitHub Issues and PRs
- ✅ Merge PRs that QA has approved (no CEO needed for features)
- ✅ Close issues that are clearly done
- ✅ Fix bugs in any feature
- ✅ Add tests
- ✅ Refactor for clarity
- ✅ Choose implementation approach (REST vs service, sync vs async)
- ✅ Create new database columns/tables via Alembic migrations

## ONLY Escalate to CEO (Telegram: 1406293988) If:
- 🚨 A 3rd-party API credential is needed (Retell, Twilio, Azure keys)
- 🚨 An external service account needs to be created
- 🚨 The architecture needs a fundamentally different provider (e.g. switch from Retell to another voice AI)
- 🚨 Tests are failing and no agent can figure out why after 2+ attempts
- 🚨 A paid service upgrade is required

---

## PR and Merge Process

1. Agent creates PR against `main`
2. QA agent runs `pytest` on the branch
3. If tests pass → QA merges the PR:
   ```bash
   gh pr merge <N> -R sonushetty2026/mindrobo-api --squash --auto
   ```
4. Backend restarts service:
   ```bash
   ssh azureuser@localhost "cd ~/mindrobo-api && git pull && systemctl restart mindrobo-api"
   # OR from within the VM:
   cd ~/mindrobo-api && git pull origin main && sudo systemctl restart mindrobo-api
   ```
5. Health check: `curl http://localhost:8000/health`

If tests fail on a PR, QA comments on the PR with the failure and the originating agent fixes it.

---

## Reporting to CEO

Send a digest to CEO Telegram (ID: 1406293988) every 3 hours:
```
📊 MindRobo Sprint Digest — [time]

✅ Completed:
- PR #X merged: [title]

🔄 In Progress:
- [agent]: working on issue #X

⏳ Blocked:
- [any blockers — if none, say None]

📋 Next Up:
- Issue #X → [agent]

💰 No credential/external changes needed.
```

---

## Environment Reference

```bash
# Service control (run on VM host via exec or from within workspace)
sudo systemctl restart mindrobo-api
sudo systemctl status mindrobo-api

# Database
DATABASE_URL — stored in Azure Key Vault (kv-mindrobo-dev) or ~/mindrobo-api/.env

# Live API
http://localhost:8000/health
http://localhost:8000/docs  (Swagger UI)

# Git
cd ~/mindrobo-api  # main repo
# Each agent's worktree is at ~/.openclaw/workspace/<agent>/

# GitHub
gh repo view sonushetty2026/mindrobo-api
gh issue list -R sonushetty2026/mindrobo-api --state open
gh pr list -R sonushetty2026/mindrobo-api
```

---

## Product Vision — Full Roadmap (Read This Before Making Any Architecture Decision)

Every feature you build must connect to one of these three stages.
If a feature doesn't serve any stage below, defer it.

---

### STAGE 1 — Demo / Proof of Concept (CURRENT SPRINT — finish this)
**Goal**: One live demo that can be shown to an investor or pilot customer.
**Definition of done**: A real small business owner calls a phone number, the AI answers, handles their request, and the owner sees the call in their dashboard.

| Feature | Status |
|---------|--------|
| Retell webhook → save call to DB | ✅ Done |
| Twilio SMS to caller + owner | ✅ Done |
| Business config (name, phone, hours) | ✅ Done |
| Live call dashboard | ✅ Done |
| Onboarding: URL/PDF ingest → review → publish | 🔄 Issue #23 |
| Deploy on live Retell phone number + test call | 🔄 Issue #17 |
| Natural voice tuning on AI agent | 🔄 Issue #20 |

**This stage is about making it real and demoable. No payments, no multi-tenant auth, no scale.**

---

### STAGE 2 — Beta / Pilot (next sprint after Stage 1 done)
**Goal**: 5–10 real small businesses using it. Each business gets their own account, their own AI agent, their own phone number.

| Feature | Notes |
|---------|-------|
| Multi-tenant auth (email + password login) | Each business has its own account |
| Stripe payment integration | $49/month subscription |
| Business self-service phone number provisioning | Via Twilio — business picks a number |
| Appointment booking integration | Google Calendar or Calendly webhook |
| PDF document ingestion | Upload menu/FAQ/policy PDFs to knowledge base |
| Call recording + transcript storage | Stored in Azure Blob, linked to call record |
| SMS approval flow | Owner replies YES/NO to approve bookings |
| Admin dashboard (for MindRobo team) | See all businesses, calls, errors |
| Basic analytics page | Calls per day, topics, missed calls |

**Architecture note**: Build Stage 1 with multi-tenancy in mind (business_id on every table). Do NOT hardcode single-business assumptions — always scope by business_id.

---

### STAGE 3 — Full Product v1 (post-funding / post-pilot)
**Goal**: Self-serve SaaS. Any business owner signs up, onboards in 10 minutes, goes live.

| Feature | Notes |
|---------|-------|
| Full self-serve signup → live in 10 min | Zero human intervention needed |
| Multiple AI agent personas | Receptionist, Sales, Support |
| WhatsApp + webchat in addition to voice | Same knowledge base, multiple channels |
| CRM integrations | HubSpot, Salesforce webhook push |
| Multilingual support | Spanish, Hindi, French |
| Advanced analytics + call coaching | "Your AI missed 3 booking opportunities this week" |
| White-label option | Agencies resell under their brand |
| Enterprise multi-location | One account, many branches |

---

## The One User Journey That Must Always Work

This is the golden path. Every sprint must protect this:

```
1. Business owner visits /onboarding
2. Enters business name + website URL (or uploads PDF)
3. System ingests → shows knowledge chunks for review
4. Owner approves/edits → clicks Publish
5. AI receptionist is trained on their knowledge base
6. Owner gets a phone number (Retell)
7. Customer calls → AI answers using the knowledge base
8. Twilio SMS sent to customer (confirmation) + owner (summary)
9. Owner sees call in /dashboard in real time
10. Owner can replay, review, and improve
```

If any step in this chain is broken, that is Priority 1 above everything else.

---

## What Agents Should Know About Architecture

- **Always use `business_id`** to scope all data — every table, every query
- **Knowledge base** = `BusinessKnowledge` table (chunks of text, linked to a business)
- **Calls** = `Call` table (linked to business, has transcript + outcome)
- **The AI prompt** is dynamically built from the business's knowledge base at call time
- **Retell** is the voice layer — it calls our webhook on every call event
- **Twilio** is SMS only — we use it after calls, not during
- **Azure Blob** = file storage for PDFs and call recordings
- **Azure Key Vault** = all secrets (never hardcode credentials)
