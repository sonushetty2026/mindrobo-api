#!/usr/bin/env python3
"""Setup script: configure Retell.ai agent webhook URL.

Usage:
    # List all agents and their current webhook URLs:
    python scripts/setup_retell_webhook.py --list

    # Set webhook URL for all agents:
    python scripts/setup_retell_webhook.py --webhook-url http://52.159.104.87:8000/api/v1/webhooks/retell

    # Set webhook URL for a specific agent:
    python scripts/setup_retell_webhook.py --webhook-url http://52.159.104.87:8000/api/v1/webhooks/retell --agent-id <id>

Requires:
    RETELL_API_KEY environment variable (or in .env / ~/secrets/db.env)
"""

import argparse
import json
import os
import sys

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)

RETELL_BASE_URL = "https://api.retellai.com"


def get_api_key() -> str:
    key = os.environ.get("RETELL_API_KEY", "")
    if not key:
        # Try loading from .env file
        for env_path in [".env", os.path.expanduser("~/secrets/db.env")]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("RETELL_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            if key:
                break
    if not key:
        print("ERROR: RETELL_API_KEY not found in environment or .env files")
        sys.exit(1)
    return key


def headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def list_agents(api_key: str) -> list:
    resp = httpx.get(f"{RETELL_BASE_URL}/list-agents", headers=headers(api_key))
    resp.raise_for_status()
    return resp.json()


def update_agent_webhook(api_key: str, agent_id: str, webhook_url: str) -> dict:
    payload = {
        "webhook_url": webhook_url,
        "webhook_events": ["call_started", "call_ended", "call_analyzed"],
    }
    resp = httpx.patch(
        f"{RETELL_BASE_URL}/update-agent/{agent_id}",
        headers=headers(api_key),
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Configure Retell.ai agent webhook URL")
    parser.add_argument("--list", action="store_true", help="List all agents and their webhook URLs")
    parser.add_argument("--webhook-url", type=str, help="Webhook URL to set")
    parser.add_argument("--agent-id", type=str, help="Specific agent ID (if omitted, applies to all agents)")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.list or not args.webhook_url:
        agents = list_agents(api_key)
        if not agents:
            print("No agents found in your Retell account.")
            return
        print(f"\n{'Agent ID':<40} {'Name':<30} {'Webhook URL'}")
        print("-" * 110)
        for agent in agents:
            agent_id = agent.get("agent_id", "?")
            name = agent.get("agent_name", "(unnamed)")
            webhook = agent.get("webhook_url") or "(not set)"
            print(f"{agent_id:<40} {name:<30} {webhook}")
        print(f"\nTotal: {len(agents)} agent(s)")
        return

    if args.webhook_url:
        if args.agent_id:
            # Update single agent
            print(f"Updating agent {args.agent_id}...")
            result = update_agent_webhook(api_key, args.agent_id, args.webhook_url)
            print(f"  ✅ {result.get('agent_id')} → {args.webhook_url}")
        else:
            # Update all agents
            agents = list_agents(api_key)
            if not agents:
                print("No agents found.")
                return
            print(f"Updating {len(agents)} agent(s)...")
            for agent in agents:
                agent_id = agent["agent_id"]
                try:
                    update_agent_webhook(api_key, agent_id, args.webhook_url)
                    print(f"  ✅ {agent_id} ({agent.get('agent_name', '?')}) → {args.webhook_url}")
                except Exception as e:
                    print(f"  ❌ {agent_id}: {e}")
        print("\nDone. Webhook events: call_started, call_ended, call_analyzed")


if __name__ == "__main__":
    main()
