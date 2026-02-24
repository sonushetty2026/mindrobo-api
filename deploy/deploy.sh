#!/bin/bash
set -e

export HOME=/home/azureuser
LOG=/home/azureuser/deploy.log
TELEGRAM_BOT=8205349591:AAFotSmtzUaJesQEb5wQPvvmKHjGEuvXVSE
CEO_CHAT=1406293988

echo "$(date) - Deploy started" >> "$LOG"

cd /home/azureuser/mindrobo-api
git config --global --add safe.directory /home/azureuser/mindrobo-api 2>/dev/null || true
set -a && source /home/azureuser/secrets/db.env && set +a

# Pull latest code
git pull origin main >> "$LOG" 2>&1

# Install dependencies
.venv/bin/pip install -r requirements.txt -q >> "$LOG" 2>&1

# Run migrations — FATAL on failure (Issue #117 Rule 3)
.venv/bin/alembic upgrade head >> "$LOG" 2>&1 || {
    echo "$(date) - FATAL: alembic upgrade head FAILED" >> "$LOG"
    MSG="🚨 DEPLOY FAILED! Migration failed after git pull. Check deploy.log immediately."
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT/sendMessage" -d "chat_id=$CEO_CHAT" -d "text=$MSG" > /dev/null 2>&1
    echo "000"
    exit 1
}

# Restart service
sudo systemctl restart mindrobo-api
sleep 5

# Health check
STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health)
echo "$(date) - Deploy finished. Health: $STATUS" >> "$LOG"

if [ "$STATUS" != "200" ]; then
    MSG="🚨 DEPLOY FAILED! Health check returned $STATUS after restart. Check deploy.log."
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT/sendMessage" -d "chat_id=$CEO_CHAT" -d "text=$MSG" > /dev/null 2>&1
    echo "000"
    exit 1
fi

echo "$STATUS"
