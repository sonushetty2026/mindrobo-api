#!/bin/bash
set -e

LOG=/home/azureuser/deploy.log
echo "$(date) — Deploy started" >> "$LOG"

cd /home/azureuser/mindrobo-api

# Load environment variables
set -a && source /home/azureuser/secrets/db.env && set +a

# Pull latest code
git pull origin main >> "$LOG" 2>&1

# Install dependencies
.venv/bin/pip install -r requirements.txt >> "$LOG" 2>&1

# Run migrations
alembic upgrade head >> "$LOG" 2>&1

# Restart the service
systemctl restart mindrobo-api

# Wait for service to start
sleep 5

# Health check
STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health)
echo "$(date) — Deploy finished. Health: $STATUS" >> "$LOG"

echo "$STATUS"
