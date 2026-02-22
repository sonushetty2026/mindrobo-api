# Scripts

## setup_retell_webhook.py

Configures the Retell.ai agent webhook URL to point to our FastAPI server.

### Prerequisites
- `RETELL_API_KEY` set in environment, `.env`, or `~/secrets/db.env`
- `httpx` installed (`pip install httpx`)

### Usage

```bash
# List all agents and their current webhook URLs
python scripts/setup_retell_webhook.py --list

# Point all agents to our webhook endpoint
python scripts/setup_retell_webhook.py --webhook-url http://52.159.104.87:8000/api/v1/webhooks/retell

# Point a specific agent
python scripts/setup_retell_webhook.py --webhook-url http://52.159.104.87:8000/api/v1/webhooks/retell --agent-id <agent_id>
```

### What it does
- Sets `webhook_url` on the Retell agent to receive call events
- Subscribes to events: `call_started`, `call_ended`, `call_analyzed`
- These events hit our `/api/v1/webhooks/retell` endpoint, which saves the call and triggers SMS
