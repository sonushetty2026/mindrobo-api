#!/bin/bash
set -e

echo "🚀 Starting MindRobo API deployment..."

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

# Run migrations (with fallback)
echo "🗃️  Running database migrations..."
alembic upgrade head || {
    echo "⚠️  Migration failed, attempting to continue..."
    echo "Check alembic logs above for details"
}

# Restart service
echo "🔄 Restarting API service..."
sudo systemctl restart mindrobo-api

# Check status
echo "✅ Checking service status..."
sudo systemctl status mindrobo-api --no-pager

echo "🎉 Deployment complete!"
