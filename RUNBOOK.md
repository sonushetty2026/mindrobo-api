# MindRobo Runbook — Nova's Operating Guide

Read this before any deployment, testing, or debugging task.

---

## SSH Access to VM

Nova has full SSH access. The key is in her workspace:

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87
```

**Or run a single command without opening a shell:**
```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 "your command here"
```

---

## Deploy New Code After a PR Merges

The auto-deploy cron runs every 5 minutes. To deploy immediately:

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "cd ~/mindrobo-api && git pull origin main && source ~/secrets/db.env && \
   PYTHONPATH=. .venv/bin/alembic upgrade head && sudo systemctl restart mindrobo-api"
```

---

## Run Database Migrations

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "cd ~/mindrobo-api && source ~/secrets/db.env && PYTHONPATH=. .venv/bin/alembic upgrade head"
```

---

## Check If App Is Running

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "curl -s http://localhost:8000/health"
```

Expected: `{"status":"ok","service":"mindrobo-api","version":"0.1.0"}`

---

## Restart the Service

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "sudo systemctl restart mindrobo-api"
```

---

## Check Service Logs (Debug Errors)

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "sudo journalctl -u mindrobo-api -n 50 --no-pager"
```

---

## Run Retell Webhook Setup Script

After any deploy that changes webhook config:

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "cd ~/mindrobo-api && source ~/secrets/db.env && \
   .venv/bin/python scripts/setup_retell_webhook.py --webhook-url http://52.159.104.87:8000/api/v1/webhooks/retell"
```

---

## Simulate a Call (No Real Phone Needed)

To test the full loop without making an actual call, POST fake call data directly to the webhook:

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "curl -s -X POST http://localhost:8000/api/v1/webhooks/retell \
   -H 'Content-Type: application/json' \
   -d '{
     \"event\": \"call_ended\",
     \"call\": {
       \"call_id\": \"test_call_001\",
       \"agent_id\": \"agent_d791c6f5f5ce774b523ab3d81c\",
       \"from_number\": \"+12345678901\",
       \"to_number\": \"+18149195019\",
       \"call_status\": \"ended\",
       \"duration_ms\": 45000,
       \"transcript\": \"Caller: Hi my name is John Smith, I need a roof repair urgently, water is coming in. Address is 123 Main Street.\",
       \"call_analysis\": {
         \"custom_analysis_data\": {
           \"lead_name\": \"John Smith\",
           \"service_type\": \"roof repair\",
           \"urgency\": \"high\",
           \"address\": \"123 Main Street\",
           \"outcome\": \"lead captured\"
         }
       }
     }
   }'"
```

**Then verify:**
1. Check dashboard: `http://52.159.104.87:8000/dashboard`
2. Check auto-deploy log: `tail -30 /tmp/autodeploy.log`

---

## Check Auto-Deploy Log

```bash
ssh -i ~/.openclaw/workspace/vm_key.pem -o StrictHostKeyChecking=no azureuser@52.159.104.87 \
  "tail -30 /tmp/autodeploy.log"
```

---

## Environment Variables (on VM)

All secrets live in `/home/azureuser/secrets/db.env`:
- `DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `RETELL_API_KEY` — Retell.ai API key
- `AZURE_STORAGE_ACCOUNT` — mindrobostorage001
- `KEY_VAULT_NAME` — kv-mindrobo-dev
- `PG_HOST`, `PG_DB`, `PG_USER` — Postgres connection parts

**Never put secrets in code or PRs.**

---

## GitHub PAT (for pushing code)

```bash
cat /home/azureuser/secrets/github_pat_mindrobo_api.txt
```

Use this to authenticate git operations for `sonushetty2026/mindrobo-api`.

---

## What "Demo Complete" Looks Like

1. POST simulated call to webhook → 200 OK
2. `http://52.159.104.87:8000/dashboard` shows the call
3. SMS received on owner phone: lead name, service, urgency
4. SMS received on caller phone: confirmation

When all 4 are verified → ping Prashant: "Demo is live. Full loop working."
