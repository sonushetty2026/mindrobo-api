"""Security service for brute force protection and login attempt tracking.

Issue #101: Track failed login attempts per IP, enforce rate limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# In-memory storage for failed login attempts
# Structure: {ip_address: [(timestamp, email), ...]}
failed_attempts: dict[str, list[tuple[datetime, str]]] = {}

# Configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxy headers."""
    # Check X-Forwarded-For header first (for proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


def cleanup_old_attempts(ip: str):
    """Remove attempts older than the lockout duration."""
    if ip not in failed_attempts:
        return
    
    cutoff = datetime.utcnow() - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    failed_attempts[ip] = [
        (ts, email) for ts, email in failed_attempts[ip]
        if ts > cutoff
    ]
    
    # Remove IP entirely if no recent attempts
    if not failed_attempts[ip]:
        del failed_attempts[ip]


def record_failed_login(request: Request, email: str):
    """Record a failed login attempt for an IP address."""
    ip = get_client_ip(request)
    
    # Clean up old attempts first
    cleanup_old_attempts(ip)
    
    # Add new attempt
    if ip not in failed_attempts:
        failed_attempts[ip] = []
    
    failed_attempts[ip].append((datetime.utcnow(), email))
    
    logger.warning(
        "Failed login attempt for %s from IP %s (%d recent attempts)",
        email,
        ip,
        len(failed_attempts[ip])
    )


def check_rate_limit(request: Request) -> Optional[HTTPException]:
    """Check if IP has exceeded failed login rate limit.
    
    Returns HTTPException if rate limit exceeded, None otherwise.
    """
    ip = get_client_ip(request)
    
    # Clean up old attempts
    cleanup_old_attempts(ip)
    
    # Check current attempt count
    if ip in failed_attempts and len(failed_attempts[ip]) >= MAX_FAILED_ATTEMPTS:
        # Calculate time until lockout expires
        oldest_attempt = min(ts for ts, _ in failed_attempts[ip])
        unlock_time = oldest_attempt + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        minutes_remaining = int((unlock_time - datetime.utcnow()).total_seconds() / 60) + 1
        
        logger.error(
            "Rate limit exceeded for IP %s (%d attempts). Locked for %d more minutes.",
            ip,
            len(failed_attempts[ip]),
            minutes_remaining
        )
        
        return HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {minutes_remaining} minutes."
        )
    
    return None


def clear_failed_attempts(request: Request):
    """Clear failed login attempts for an IP (called on successful login)."""
    ip = get_client_ip(request)
    
    if ip in failed_attempts:
        del failed_attempts[ip]
        logger.info("Cleared failed login attempts for IP %s", ip)


def get_failed_login_attempts(limit: int = 100) -> list[dict]:
    """Get recent failed login attempts for admin monitoring.
    
    Returns list of dicts with ip, email, timestamp, attempt_count.
    """
    # Clean up old attempts from all IPs first
    for ip in list(failed_attempts.keys()):
        cleanup_old_attempts(ip)
    
    # Build response
    result = []
    for ip, attempts in failed_attempts.items():
        # Group attempts by email
        email_counts = {}
        for ts, email in attempts:
            if email not in email_counts:
                email_counts[email] = {"count": 0, "last_attempt": ts}
            email_counts[email]["count"] += 1
            email_counts[email]["last_attempt"] = max(email_counts[email]["last_attempt"], ts)
        
        # Add entry for each email
        for email, data in email_counts.items():
            result.append({
                "ip": ip,
                "email": email,
                "attempt_count": data["count"],
                "last_attempt": data["last_attempt"].isoformat(),
                "is_locked": len(attempts) >= MAX_FAILED_ATTEMPTS,
            })
    
    # Sort by most recent first
    result.sort(key=lambda x: x["last_attempt"], reverse=True)
    
    return result[:limit]
