# GitHub Webhook Auto-Deploy Setup

This system enables automatic deployment of the MindRobo API when code is pushed to the `main` branch on GitHub.

## Architecture

1. **GitHub webhook** → sends POST to your server on push
2. **webhook_server.py** → validates signature, triggers deploy
3. **deploy.sh** → pulls code, installs deps, runs migrations, restarts service
4. **systemd service** → keeps webhook server running

## Prerequisites

- Server: 52.159.104.87
- App installed at: `/home/azureuser/mindrobo-api`
- Python venv at: `/home/azureuser/mindrobo-api/.venv`
- Environment file: `/home/azureuser/secrets/db.env`
- Main app service: `mindrobo-api.service`

## Installation Steps

### 1. Install Flask Dependency

```bash
cd /home/azureuser/mindrobo-api
.venv/bin/pip install flask requests
```

### 2. Make Deploy Script Executable

```bash
chmod +x /home/azureuser/mindrobo-api/deploy/deploy.sh
```

### 3. Generate Webhook Secret

```bash
# Generate a secure random secret
openssl rand -hex 32
```

**Save this secret** — you'll need it for both the environment file and GitHub webhook configuration.

### 4. Add Environment Variables

Edit `/home/azureuser/secrets/db.env` and add:

```bash
# Required for webhook signature validation
GITHUB_WEBHOOK_SECRET=your_generated_secret_here

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 5. Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp /home/azureuser/mindrobo-api/deploy/mindrobo-webhook.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the webhook service
sudo systemctl enable mindrobo-webhook
sudo systemctl start mindrobo-webhook

# Check status
sudo systemctl status mindrobo-webhook
```

### 6. Open Port 9000 in Azure NSG

In Azure Portal:

1. Navigate to your VM → **Networking** → **Network settings**
2. Click **Create port rule** → **Inbound port rule**
3. Configure:
   - **Source**: Any (GitHub webhook IPs vary)
   - **Source port ranges**: *
   - **Destination**: Any
   - **Destination port ranges**: 9000
   - **Protocol**: TCP
   - **Action**: Allow
   - **Priority**: 310 (or next available)
   - **Name**: AllowWebhook9000
4. Click **Add**

### 7. Configure GitHub Webhook

In your GitHub repository (https://github.com/sonushetty2026/mindrobo-api):

1. Go to **Settings** → **Webhooks** → **Add webhook**
2. Configure:
   - **Payload URL**: `http://52.159.104.87:9000/deploy`
   - **Content type**: `application/json`
   - **Secret**: (paste the secret from step 3)
   - **Which events**: Just the push event
   - **Active**: ✓ Checked
3. Click **Add webhook**

GitHub will send a test ping. Check the webhook delivery status to verify it's working.

## Testing

### Test the Webhook Server Manually

```bash
# Check if webhook server is running
curl http://localhost:9000/health

# Expected: {"status":"ok","service":"mindrobo-webhook"}
```

### Test a Deploy (without GitHub)

```bash
# Run deploy script directly
sudo /home/azureuser/mindrobo-api/deploy/deploy.sh

# Check logs
tail -f /home/azureuser/deploy.log
```

### Test via GitHub

Push a commit to `main`:

```bash
git commit --allow-empty -m "test: trigger webhook deploy"
git push origin main
```

Check:
1. GitHub webhook delivery status (Settings → Webhooks → Recent Deliveries)
2. Server logs: `tail -f /home/azureuser/deploy.log`
3. Systemd logs: `journalctl -u mindrobo-webhook -f`

## Monitoring

### View Webhook Server Logs

```bash
# Real-time logs
journalctl -u mindrobo-webhook -f

# Recent logs
journalctl -u mindrobo-webhook -n 50
```

### View Deploy Logs

```bash
tail -f /home/azureuser/deploy.log
```

### Check Service Status

```bash
sudo systemctl status mindrobo-webhook
sudo systemctl status mindrobo-api
```

## Troubleshooting

### Webhook Server Not Starting

```bash
# Check for errors
journalctl -u mindrobo-webhook -e

# Common issues:
# - Flask not installed in venv
# - GITHUB_WEBHOOK_SECRET not in db.env
# - Port 9000 already in use
```

### Deploy Fails

```bash
# Run deploy script manually to see errors
sudo bash -x /home/azureuser/mindrobo-api/deploy/deploy.sh

# Common issues:
# - Git conflicts
# - Missing dependencies
# - Database migration errors
# - Service restart permissions
```

### GitHub Webhook Shows Errors

Check Recent Deliveries in GitHub:
- **403 Forbidden**: Signature mismatch — verify secret matches in both places
- **Connection refused**: Port 9000 not open or webhook server not running
- **Timeout**: Deploy script taking too long (>10s GitHub timeout is OK, deploy continues)

## Security Notes

- The webhook secret MUST match between GitHub and db.env
- Never commit the webhook secret to the repository
- The deploy script runs with azureuser permissions — it needs sudo access for `systemctl restart`
- Add `azureuser ALL=(ALL) NOPASSWD: /bin/systemctl restart mindrobo-api` to `/etc/sudoers` if restart fails

## Telegram Notifications (Optional)

If you want deploy notifications in Telegram:

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Add to db.env:
   ```bash
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=-1001234567890
   ```
4. Restart webhook service: `sudo systemctl restart mindrobo-webhook`

## Maintenance

### Restart Webhook Server

```bash
sudo systemctl restart mindrobo-webhook
```

### Stop Auto-Deploy Temporarily

```bash
sudo systemctl stop mindrobo-webhook
```

### Re-enable Auto-Deploy

```bash
sudo systemctl start mindrobo-webhook
```

### Update Webhook Code

Push changes to the `deploy/` directory and run:

```bash
cd /home/azureuser/mindrobo-api
git pull origin main
sudo systemctl restart mindrobo-webhook
```

## File Locations Summary

- Deploy script: `/home/azureuser/mindrobo-api/deploy/deploy.sh`
- Webhook server: `/home/azureuser/mindrobo-api/deploy/webhook_server.py`
- Systemd service: `/etc/systemd/system/mindrobo-webhook.service`
- Environment vars: `/home/azureuser/secrets/db.env`
- Deploy log: `/home/azureuser/deploy.log`

---

**Questions?** Check the logs first. Most issues are visible in `journalctl -u mindrobo-webhook -e`.
