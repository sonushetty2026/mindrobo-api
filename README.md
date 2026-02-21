# MindRobo API

AI Receptionist for Home Services — answers calls 24/7, captures leads, notifies owners.

## Stack
- **FastAPI** (Python 3.12)
- **Retell.ai** — voice agent, barge-in, TTS/ASR
- **Azure PostgreSQL Flexible Server** — call logs, leads, transcripts
- **Azure Blob Storage** — recordings, uploaded docs
- **Azure Key Vault** — secrets management
- **Twilio** — SMS notifications

## Quick start
```bash
cp .env.example .env
# fill in your credentials
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Key endpoints
- `GET /health` — health check
- `POST /api/v1/webhooks/retell` — Retell.ai event webhook
- `GET /api/v1/calls/` — list recent calls
