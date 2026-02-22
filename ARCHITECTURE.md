# MindRobo Architecture

## What We Are Building

MindRobo is an AI receptionist for home-service businesses (HVAC, plumbing, roofing).
When a contractor misses a call, our system answers it via Retell.ai, captures lead info,
saves it to PostgreSQL, and sends SMS notifications via Twilio.

**The pitch:** A roofing contractor losing one missed call could lose an $8K–$25K job. We make sure that never happens.

---

## System Flow (End-to-End)

```
Caller dials Twilio number
        ↓
Retell.ai answers the call (AI voice agent)
        ↓
Retell collects: caller name, address, service needed, urgency
        ↓
Call ends → Retell fires POST to:
  http://52.159.104.87:8000/api/v1/webhooks/retell
        ↓
FastAPI webhook handler (app/api/v1/endpoints/webhooks.py):
  1. Saves call record to PostgreSQL `calls` table
  2. Looks up business owner phone from `businesses` table
  3. Sends Twilio SMS to caller (confirmation)
  4. Sends Twilio SMS to owner (lead summary + urgency)
  5. Pushes WebSocket update to /dashboard
        ↓
Dashboard (http://52.159.104.87:8000/dashboard)
  shows last 20 calls in real time
```

---

## Infrastructure

| Component | Value |
|---|---|
| VM | `azureuser@52.159.104.87` (Ubuntu 24.04) |
| SSH key | `~/.openclaw/workspace/vm_key.pem` |
| FastAPI app | `/home/azureuser/mindrobo-api` |
| Service | `systemd: mindrobo-api` (port 8000) |
| Database | Azure PostgreSQL Flexible Server |
| DB host | `mindrobo-postgres-dev.postgres.database.azure.com` |
| DB name | `mindrobo_db` |
| Blob Storage | `mindrobostorage001` |
| Key Vault | `kv-mindrobo-dev` |
| Secrets file | `/home/azureuser/secrets/db.env` on VM |

---

## GitHub Repos

| Repo | Purpose |
|---|---|
| `sonushetty2026/mindrobo-api` | Product code (FastAPI) |
| `sonushetty2026/agent-company-os` | Ops, docs, agent config |

**PAT for mindrobo-api:** stored at `/home/azureuser/secrets/github_pat_mindrobo_api.txt` on VM

---

## Retell.ai Agents

| Agent ID | Name | Webhook |
|---|---|---|
| `agent_d791c6f5f5ce774b523ab3d81c` | Patient Screening | `http://52.159.104.87:8000/api/v1/webhooks/retell` |
| `agent_b1287b3dc484be7223b563a836` | Healthcare Check-In | `http://52.159.104.87:8000/api/v1/webhooks/retell` |

**Retell API key:** `RETELL_API_KEY` in `/home/azureuser/secrets/db.env`

---

## Twilio

| Field | Value |
|---|---|
| Phone number | `+18149195019` |
| Account SID | see `/home/azureuser/secrets/db.env` or Azure Key Vault `kv-mindrobo-dev` |
| Credentials | In Azure Key Vault `kv-mindrobo-dev` |

---

## Database Tables

| Table | Purpose |
|---|---|
| `calls` | Every inbound call — caller phone, lead name, service type, urgency, outcome, transcript |
| `businesses` | Business config — name, owner phone, retell_agent_id, twilio_phone_number |

---

## Codebase Map

```
app/
  main.py                          # FastAPI app entrypoint, /health, /dashboard
  api/v1/endpoints/
    webhooks.py                    # POST /api/v1/webhooks/retell — core handler
    calls.py                       # GET /api/v1/calls — list/detail
    businesses.py                  # CRUD for businesses table
  models/
    call.py                        # SQLAlchemy Call model
    business.py                    # SQLAlchemy Business model
  schemas/
    call.py                        # Pydantic CallOut schema
  services/
    sms.py                         # Twilio SMS sender
alembic/                           # DB migrations
scripts/
  setup_retell_webhook.py          # Points Retell agents to our webhook URL
deploy/
  mindrobo-api.service             # systemd unit file
  README.md                        # Deploy instructions
```

---

## V1 Demo Definition

**Demo is proven when:**
1. A real or simulated call hits the Retell agent
2. `calls` table has a new row with lead data
3. Two SMS messages sent via Twilio (caller + owner)
4. Call appears on `http://52.159.104.87:8000/dashboard`

**Not in V1:** calendar booking, landing page, knowledge base, URL ingestion
