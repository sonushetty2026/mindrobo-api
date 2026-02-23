"""War Room dashboard - real-time agent status monitoring.

- GET /api/v1/warroom/ → HTML war room dashboard
- GET /api/v1/warroom/status → JSON status of all agents + sprint pipeline
"""

import logging
import subprocess
import json
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
WARROOM_TEMPLATE_PATH = TEMPLATES_DIR / "warroom.html"


def _load_warroom_template() -> str:
    if not WARROOM_TEMPLATE_PATH.exists():
        logger.error("War room template not found at %s", WARROOM_TEMPLATE_PATH)
        return "<html><body><h1>War room template not found</h1></body></html>"
    return WARROOM_TEMPLATE_PATH.read_text()


def _run_gh(args: list[str], timeout: int = 15) -> str:
    """Run a gh CLI command and return stdout."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(Path(__file__).parent)
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning("gh command failed: %s", e)
        return ""


def _get_github_data() -> dict:
    """Fetch live data from GitHub."""
    repo = "sonushetty2026/mindrobo-api"

    # Open issues
    issues_raw = _run_gh([
        "issue", "list", "-R", repo, "--state", "open",
        "--json", "number,title,labels,assignees"
    ])
    open_issues = json.loads(issues_raw) if issues_raw else []

    # Open PRs
    prs_raw = _run_gh([
        "pr", "list", "-R", repo, "--state", "open",
        "--json", "number,title,headRefName,author,reviewDecision,createdAt"
    ])
    open_prs = json.loads(prs_raw) if prs_raw else []

    # Recently closed issues (last 20)
    closed_raw = _run_gh([
        "issue", "list", "-R", repo, "--state", "closed", "--limit", "20",
        "--json", "number,title,closedAt"
    ])
    closed_issues = json.loads(closed_raw) if closed_raw else []

    # Recently merged PRs
    merged_raw = _run_gh([
        "pr", "list", "-R", repo, "--state", "merged", "--limit", "10",
        "--json", "number,title,mergedAt,headRefName"
    ])
    merged_prs = json.loads(merged_raw) if merged_raw else []

    return {
        "open_issues": open_issues,
        "open_prs": open_prs,
        "closed_issues": closed_issues,
        "merged_prs": merged_prs,
    }


# Phase 2 sprint definition
PHASE2_ISSUES = {
    58: {"title": "Marketing Website + Auth Pages", "wave": 1, "priority": 1},
    59: {"title": "Agent Personality Builder", "wave": 2, "priority": 2},
    60: {"title": "Availability Scheduler + Appointments", "wave": 3, "priority": 3},
    61: {"title": "Phone Number Setup (Twilio)", "wave": 2, "priority": 4},
    62: {"title": "Call Forwarding / Ring Timeout", "wave": 3, "priority": 5},
    63: {"title": "Call Recordings (Azure Blob)", "wave": 3, "priority": 6},
    64: {"title": "Lead Capture Storage", "wave": 4, "priority": 7},
    65: {"title": "Email Notifications (SendGrid)", "wave": 4, "priority": 8},
    66: {"title": "Subscription Management (/billing)", "wave": 4, "priority": 9},
}


def _determine_agent_status(gh_data: dict) -> list[dict]:
    """Determine each agent's current status from GitHub data."""
    open_pr_branches = {pr["headRefName"]: pr for pr in gh_data["open_prs"]}
    open_issue_nums = {i["number"] for i in gh_data["open_issues"]}

    # Map branches to agents
    branch_agent_map = {
        "feat/auth-system": "backend",
        "feat/auth-frontend": "frontend",
        "feat/agent-personality": "frontend",
        "feat/personality-and-phone": "backend",
        "feat/availability-scheduler": "ingestion",
        "feat/phone-and-scheduling-ui": "frontend",
        "feat/ring-timeout-and-recordings": "backend",
        "feat/leads-email-billing": "backend",
        "feat/leads-and-billing-ui": "frontend",
        "feat/qa-coverage-expansion": "qa",
    }

    agent_prs = {a: [] for a in ["orchestrator", "backend", "frontend", "qa", "ingestion"]}
    for branch, pr in open_pr_branches.items():
        agent_id = branch_agent_map.get(branch, "unknown")
        if agent_id in agent_prs:
            agent_prs[agent_id].append(pr)

    agents = [
        {
            "id": "orchestrator",
            "name": "Orchestrator",
            "role": "Lead engineer — coordinates all agents, reviews architecture, routes bugs",
            "model": "Opus",
            "status": "active",
            "current_task": "Coordinating Phase 2 sprint — routing QA bugs, merging PRs",
            "branch": "—",
            "prs": [],
            "color": "blue",
        },
        {
            "id": "backend",
            "name": "Backend",
            "role": "API development, database, integrations",
            "model": "Sonnet",
            "status": "active" if agent_prs["backend"] else "idle",
            "current_task": "",
            "branch": "",
            "prs": agent_prs["backend"],
            "color": "purple",
        },
        {
            "id": "frontend",
            "name": "Frontend",
            "role": "UI/UX, templates, dashboards",
            "model": "Sonnet",
            "status": "active" if agent_prs["frontend"] else "idle",
            "current_task": "",
            "branch": "",
            "prs": agent_prs["frontend"],
            "color": "cyan",
        },
        {
            "id": "qa",
            "name": "QA",
            "role": "Testing, code review, browser flow verification",
            "model": "Sonnet",
            "status": "active" if agent_prs["qa"] else "reviewing",
            "current_task": "Reviewing open PRs for bugs before merge",
            "branch": "",
            "prs": agent_prs["qa"],
            "color": "green",
        },
        {
            "id": "ingestion",
            "name": "Ingestion",
            "role": "Repurposed for backend coding this sprint",
            "model": "Sonnet",
            "status": "active" if agent_prs["ingestion"] else "idle",
            "current_task": "",
            "branch": "",
            "prs": agent_prs["ingestion"],
            "color": "orange",
        },
    ]

    # Set current task from open PRs
    for agent in agents:
        if agent["prs"]:
            pr = agent["prs"][0]
            agent["current_task"] = f"PR #{pr['number']}: {pr['title']}"
            agent["branch"] = pr["headRefName"]
        elif agent["id"] not in ("orchestrator", "qa"):
            agent["current_task"] = "Waiting for next assignment"

    return agents


def _build_pipeline(gh_data: dict) -> list[dict]:
    """Build the sprint pipeline status."""
    open_issue_nums = {i["number"] for i in gh_data["open_issues"]}
    closed_issue_nums = {i["number"] for i in gh_data["closed_issues"]}
    open_pr_nums = {pr["number"] for pr in gh_data["open_prs"]}
    merged_pr_nums = {pr["number"] for pr in gh_data["merged_prs"]}

    pipeline = []
    for num, info in sorted(PHASE2_ISSUES.items(), key=lambda x: x[1]["priority"]):
        if num in closed_issue_nums:
            status = "done"
        elif num in open_issue_nums:
            # Check if there's a PR for it
            has_open_pr = any(
                f"#{num}" in pr.get("title", "") or f"(#{num})" in pr.get("title", "")
                for pr in gh_data["open_prs"]
            )
            status = "in_review" if has_open_pr else "in_progress"
        else:
            status = "done"  # If not open, assume closed

        pipeline.append({
            "issue": num,
            "title": info["title"],
            "wave": info["wave"],
            "priority": info["priority"],
            "status": status,
        })

    return pipeline


@router.get("/", response_class=HTMLResponse)
async def warroom_page():
    return _load_warroom_template()


@router.get("/status")
async def get_agent_status():
    gh_data = _get_github_data()
    agents = _determine_agent_status(gh_data)
    pipeline = _build_pipeline(gh_data)

    done_count = sum(1 for p in pipeline if p["status"] == "done")
    total_count = len(pipeline)

    blockers = []
    # Check for any PR with review changes requested
    for pr in gh_data["open_prs"]:
        if pr.get("reviewDecision") == "CHANGES_REQUESTED":
            blockers.append(f"PR #{pr['number']} needs changes: {pr['title']}")

    return {
        "agents": agents,
        "pipeline": pipeline,
        "open_prs": [
            {
                "number": pr["number"],
                "title": pr["title"],
                "branch": pr["headRefName"],
                "created": pr.get("createdAt", ""),
            }
            for pr in gh_data["open_prs"]
        ],
        "merged_prs": [
            {
                "number": pr["number"],
                "title": pr["title"],
                "merged": pr.get("mergedAt", ""),
            }
            for pr in gh_data["merged_prs"][:5]
        ],
        "system_status": "operational",
        "active_agents": sum(1 for a in agents if a["status"] == "active"),
        "total_agents": len(agents),
        "sprint_progress": f"{done_count}/{total_count}",
        "sprint_percent": round(done_count / total_count * 100) if total_count else 0,
        "blockers": blockers,
        "last_refresh": datetime.utcnow().isoformat(),
    }
