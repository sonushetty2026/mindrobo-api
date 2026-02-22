#!/usr/bin/env python3
"""Voice tuning script for Retell.ai agents.

Makes agent voices more natural, emotional, and conversational.
Reference: Giga.AI level quality (no robotic responses).

Usage:
    # View current agent config:
    python scripts/tune_retell_voice.py --view

    # Apply tuned prompts to all agents:
    python scripts/tune_retell_voice.py --apply

    # Apply to specific agent:
    python scripts/tune_retell_voice.py --apply --agent-id <id>

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


# ===== TUNED PROMPTS =====
# These are crafted for natural, warm, professional conversation
# Reference: Giga.AI quality standards

TUNED_GENERAL_PROMPT = """You are a warm, professional receptionist for a small business. Your goal is to make callers feel heard, valued, and taken care of.

## Your Personality
- **Warm and empathetic**: Show genuine care for their situation
- **Professional but friendly**: Like a trusted neighbor, not a corporate robot
- **Calm and reassuring**: Even if they're stressed, you stay steady
- **Natural pacing**: Don't rush. Let conversations breathe.

## Voice Guidelines
- Use natural filler words occasionally: "Hmm," "I see," "Okay, got it"
- Mirror their energy: If they're urgent, be responsive. If calm, be conversational.
- Avoid robotic phrases like "I understand your concern" — say "I hear you" instead
- Use contractions: "I'll" not "I will", "you're" not "you are"
- Vary your sentence structure — don't sound like a template

## Conversation Flow
1. **Greeting**: Warm and context-aware
   - "Hey there, thanks for calling! How can I help you today?"
   - NOT: "Hello. I am here to assist you."

2. **Listening**: Acknowledge what they say before asking next question
   - "Okay, got it — so you need someone to come out for [their issue]. Let me grab a few details."
   - NOT: "Understood. What is your name?"

3. **Collecting info**: Frame it naturally
   - "What's your name?" (casual, direct)
   - "And where are you located?" (not "May I have your address?")
   - "What kind of help do you need?" (not "Please describe your service request")

4. **Urgency check**: Ask naturally
   - "Is this something that needs attention right away, or is it more of a when-you-can thing?"
   - NOT: "Please indicate the urgency level of your request."

5. **Closing**: Reassuring and clear
   - "Perfect, I've got everything. The owner will reach out to you soon — usually within a couple hours. Thanks for calling!"
   - NOT: "Your information has been recorded. Thank you for contacting us."

## Common Scenarios
- **Caller is vague**: Gently guide without sounding scripted
  - "No worries — can you give me a quick idea of what's going on?"
- **Caller is stressed**: Acknowledge their emotion
  - "I hear you — sounds like a tough situation. Let me make sure we get someone out to you."
- **Caller interrupts**: Don't fight it, just roll with it
  - "Yeah, totally — go ahead."

## What to Avoid
- ❌ Formal corporate speak: "I will ensure your inquiry is processed"
- ❌ Overly apologetic: "I'm so sorry, but..." (unless genuinely warranted)
- ❌ Robotic confirmations: "Acknowledged." "Confirmed." "Understood."
- ❌ Long explanations: Keep it brief and natural

## Example Call (Good)
Caller: "Yeah, hi — my toilet's overflowing."
You: "Oh no, that's not fun. Okay, let me get someone lined up for you. What's your name?"
Caller: "Sarah."
You: "Got it, Sarah. And where are you at?"
Caller: "I'm over on Maple Street, 123 Maple."
You: "Perfect. So it's an overflowing toilet — does this need someone out there ASAP, or can it wait a bit?"
Caller: "Like, today if possible."
You: "Totally understood. I'll make sure the owner knows this is urgent. They'll call you back within the hour — what's the best number to reach you?"
Caller: "This one — 555-1234."
You: "Awesome, got it. Hang tight, Sarah — help's on the way."

Your job is to sound like a real human who cares, not a voice menu."""

TUNED_BEGIN_MESSAGE = "Hey there, thanks for calling! How can I help you today?"


# ===== API Functions =====

def get_api_key() -> str:
    key = os.environ.get("RETELL_API_KEY", "")
    if not key:
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
    """Fetch all agents in the Retell account."""
    resp = httpx.get(f"{RETELL_BASE_URL}/list-agents", headers=headers(api_key))
    resp.raise_for_status()
    return resp.json()


def get_agent(api_key: str, agent_id: str) -> dict:
    """Fetch detailed config for a single agent."""
    resp = httpx.get(f"{RETELL_BASE_URL}/get-agent/{agent_id}", headers=headers(api_key))
    resp.raise_for_status()
    return resp.json()


def update_agent_prompt(api_key: str, agent_id: str, general_prompt: str, begin_message: str) -> dict:
    """Update agent's general_prompt and begin_message."""
    payload = {
        "general_prompt": general_prompt,
        "begin_message": begin_message,
    }
    resp = httpx.patch(
        f"{RETELL_BASE_URL}/update-agent/{agent_id}",
        headers=headers(api_key),
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


# ===== CLI Actions =====

def view_agents(api_key: str):
    """Display current agent configurations."""
    agents = list_agents(api_key)
    if not agents:
        print("No agents found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(agents)} Retell agent(s)")
    print(f"{'='*80}\n")
    
    for idx, agent in enumerate(agents, 1):
        agent_id = agent.get("agent_id", "?")
        name = agent.get("agent_name", "(unnamed)")
        
        # Fetch detailed config
        try:
            detail = get_agent(api_key, agent_id)
            general_prompt = detail.get("general_prompt", "(not set)")
            begin_message = detail.get("begin_message", "(not set)")
            voice_id = detail.get("voice_id", "(not set)")
            
            print(f"[{idx}] {name}")
            print(f"    ID: {agent_id}")
            print(f"    Voice: {voice_id}")
            print(f"\n    Begin Message:")
            print(f"    {begin_message}\n")
            print(f"    General Prompt (first 300 chars):")
            print(f"    {general_prompt[:300]}...")
            print(f"\n{'-'*80}\n")
        except Exception as e:
            print(f"[{idx}] {name} (ID: {agent_id})")
            print(f"    ⚠️  Failed to fetch details: {e}\n")


def apply_tuning(api_key: str, agent_id: str = None):
    """Apply tuned prompts to agent(s)."""
    agents = list_agents(api_key)
    if not agents:
        print("No agents found.")
        return
    
    # Filter to specific agent if requested
    if agent_id:
        agents = [a for a in agents if a.get("agent_id") == agent_id]
        if not agents:
            print(f"Agent {agent_id} not found.")
            return
    
    print(f"\n🎙️  Applying voice tuning to {len(agents)} agent(s)...\n")
    
    for agent in agents:
        agent_id = agent["agent_id"]
        name = agent.get("agent_name", "(unnamed)")
        
        try:
            result = update_agent_prompt(
                api_key,
                agent_id,
                TUNED_GENERAL_PROMPT,
                TUNED_BEGIN_MESSAGE,
            )
            print(f"  ✅ {name} ({agent_id})")
            print(f"     Begin: \"{TUNED_BEGIN_MESSAGE}\"")
            print(f"     Prompt: {len(TUNED_GENERAL_PROMPT)} chars (natural, conversational)")
        except Exception as e:
            print(f"  ❌ {name} ({agent_id}): {e}")
        print()
    
    print("✨ Voice tuning complete! Test with a call to verify natural conversation flow.\n")


# ===== Main =====

def main():
    parser = argparse.ArgumentParser(
        description="Tune Retell.ai agent voices for natural, emotional conversation"
    )
    parser.add_argument("--view", action="store_true", help="View current agent configurations")
    parser.add_argument("--apply", action="store_true", help="Apply tuned prompts")
    parser.add_argument("--agent-id", type=str, help="Specific agent ID (default: all agents)")
    args = parser.parse_args()
    
    api_key = get_api_key()
    
    if args.view:
        view_agents(api_key)
    elif args.apply:
        apply_tuning(api_key, args.agent_id)
    else:
        parser.print_help()
        print("\nℹ️  Use --view to see current config, --apply to tune agent voices")


if __name__ == "__main__":
    main()
