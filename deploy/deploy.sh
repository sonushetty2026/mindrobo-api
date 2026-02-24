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

git pull origin main >> "$LOG" 2>&1
.venv/bin/pip install -r requirements.txt -q >> "$LOG" 2>&1
.venv/bin/alembic upgrade head >> "$LOG" 2>&1 || echo "$(date) - WARNING: alembic upgrade failed" >> "$LOG"

sudo systemctl restart mindrobo-api
sleep 5

STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health)
echo "$(date) - Deploy finished. Health: $STATUS" >> "$LOG"

if [ "$STATUS" != "200" ]; then
    MSG="DEPLOY FAILED! Health check returned $STATUS. Check deploy.log on server."
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT/sendMessage" -d "chat_id=$CEO_CHAT" -d "text=$MSG" > /dev/null 2>&1
    echo "000"
    exit 1
fi

echo "$STATUS"
