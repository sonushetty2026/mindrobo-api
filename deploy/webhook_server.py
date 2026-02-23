#!/usr/bin/env python3
"""
GitHub Webhook Auto-Deploy Server for MindRobo API
Listens on port 9000, validates webhook signatures, and triggers deploys.
"""

import os
import hmac
import hashlib
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(levelname)s — %(message)s',
    handlers=[
        logging.FileHandler('/home/azureuser/deploy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration from environment
WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', '').encode('utf-8')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DEPLOY_SCRIPT = '/home/azureuser/mindrobo-api/deploy/deploy.sh'


def verify_signature(payload_body, signature_header):
    """Verify the GitHub webhook signature."""
    if not signature_header or not WEBHOOK_SECRET:
        return False
    
    hash_object = hmac.new(WEBHOOK_SECRET, msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


def send_telegram_notification(message):
    """Send deployment result to Telegram if configured."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")


def run_deploy():
    """Execute the deployment script and return the result."""
    try:
        result = subprocess.run(
            ['bash', DEPLOY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        health_code = result.stdout.strip() if result.returncode == 0 else "000"
        output = f"{result.stdout}\n{result.stderr}".strip()
        
        return {
            'success': result.returncode == 0,
            'health_code': health_code,
            'output': output
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'health_code': '000',
            'output': 'Deploy timed out after 5 minutes'
        }
    except Exception as e:
        return {
            'success': False,
            'health_code': '000',
            'output': str(e)
        }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'mindrobo-webhook'}), 200


@app.route('/deploy', methods=['POST'])
def deploy():
    """GitHub webhook endpoint for auto-deploy."""
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 403
    
    # Parse payload
    payload = request.json
    ref = payload.get('ref', '')
    
    # Only deploy on push to main
    if ref != 'refs/heads/main':
        logger.info(f"Ignoring push to {ref} (not main)")
        return jsonify({'status': 'ignored', 'message': f'Not main branch: {ref}'}), 200
    
    # Extract commit info
    commit_msg = payload.get('head_commit', {}).get('message', 'Unknown commit')
    pusher = payload.get('pusher', {}).get('name', 'Unknown')
    
    logger.info(f"Deploy triggered by {pusher}: {commit_msg}")
    
    # Run deployment
    result = run_deploy()
    
    # Prepare response
    status_text = 'success' if result['success'] else 'failure'
    response = {
        'status': status_text,
        'health_code': result['health_code'],
        'output': result['output']
    }
    
    # Send Telegram notification
    emoji = '✅' if result['success'] else '❌'
    notification = (
        f"{emoji} **Deploy {status_text.upper()}**\n\n"
        f"**Commit:** {commit_msg}\n"
        f"**Pusher:** {pusher}\n"
        f"**Health:** {result['health_code']}\n"
        f"**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    send_telegram_notification(notification)
    
    logger.info(f"Deploy finished: {status_text} (health: {result['health_code']})")
    
    return jsonify(response), 200 if result['success'] else 500


if __name__ == '__main__':
    if not WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not set - webhook security disabled!")
    
    logger.info("Starting MindRobo webhook server on port 9000...")
    app.run(host='0.0.0.0', port=9000, debug=False)
