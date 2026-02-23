#!/bin/bash
set -e

echo "🚀 Starting MindRobo API deployment (STRICT MODE)..."

# Navigate to project directory
cd /home/azureuser/mindrobo-api

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run migrations (MUST SUCCEED)
echo "🗃️  Running database migrations..."
alembic upgrade head  # NO fallback - deployment fails if this fails

# Restart service
echo "🔄 Restarting API service..."
sudo systemctl restart mindrobo-api

# Check status
echo "✅ Checking service status..."
sudo systemctl status mindrobo-api --no-pager

echo "🎉 Deployment complete!"
