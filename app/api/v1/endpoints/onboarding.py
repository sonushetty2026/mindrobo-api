"""Self-serve onboarding for business owners.

- GET /api/v1/onboarding/ → signup form
- POST /api/v1/onboarding/signup → create business + link Retell agent
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessOut

router = APIRouter()
logger = logging.getLogger(__name__)


ONBOARDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindRobo — Get Started</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .container { width: 100%; max-width: 480px; padding: 24px; }
  h1 { font-size: 1.8rem; color: #38bdf8; margin-bottom: 8px; }
  .subtitle { color: #94a3b8; margin-bottom: 32px; font-size: 0.95rem; }
  form { display: flex; flex-direction: column; gap: 16px; }
  label { font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
  input, select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-size: 1rem; outline: none; }
  input:focus, select:focus { border-color: #38bdf8; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  button { padding: 14px; border-radius: 8px; border: none; background: #38bdf8; color: #0f172a; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #0ea5e9; }
  button:disabled { background: #475569; cursor: not-allowed; }
  .success { background: #065f46; border: 1px solid #10b981; border-radius: 8px; padding: 20px; text-align: center; display: none; }
  .success h2 { color: #10b981; margin-bottom: 8px; }
  .error { color: #f87171; font-size: 0.9rem; display: none; margin-top: 8px; }
  .features { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 32px; }
  .feature { background: #1e293b; border-radius: 8px; padding: 12px; text-align: center; }
  .feature-icon { font-size: 1.5rem; margin-bottom: 4px; }
  .feature-text { font-size: 0.8rem; color: #94a3b8; }
</style>
</head>
<body>
<div class="container">
  <h1>📞 MindRobo</h1>
  <p class="subtitle">Never miss a customer call again. AI answers 24/7, captures leads, texts you the summary.</p>

  <div class="features">
    <div class="feature"><div class="feature-icon">🤖</div><div class="feature-text">AI answers calls</div></div>
    <div class="feature"><div class="feature-icon">📋</div><div class="feature-text">Captures lead info</div></div>
    <div class="feature"><div class="feature-icon">📱</div><div class="feature-text">SMS to you + caller</div></div>
    <div class="feature"><div class="feature-icon">📊</div><div class="feature-text">Live dashboard</div></div>
  </div>

  <form id="signup-form">
    <div class="field">
      <label for="name">Business Name *</label>
      <input type="text" id="name" name="name" required placeholder="e.g. Smith's Plumbing">
    </div>
    <div class="field">
      <label for="owner_name">Your Name *</label>
      <input type="text" id="owner_name" name="owner_name" required placeholder="e.g. John Smith">
    </div>
    <div class="field">
      <label for="owner_phone">Your Phone Number *</label>
      <input type="tel" id="owner_phone" name="owner_phone" required placeholder="+1 (555) 123-4567">
    </div>
    <div class="field">
      <label for="owner_email">Email</label>
      <input type="email" id="owner_email" name="owner_email" placeholder="john@smithplumbing.com">
    </div>
    <div class="field">
      <label for="service_types">What services do you offer?</label>
      <input type="text" id="service_types" name="service_types" placeholder="e.g. Plumbing, drain cleaning, water heater">
    </div>
    <div class="error" id="error-msg"></div>
    <button type="submit" id="submit-btn">Get Started — It's Free</button>
  </form>

  <div class="success" id="success-msg">
    <h2>🎉 You're all set!</h2>
    <p>Your AI receptionist is being configured. We'll text you at <strong id="confirm-phone"></strong> when it's ready.</p>
    <p style="margin-top: 12px; color: #94a3b8; font-size: 0.85rem;">Check your dashboard: <a href="/dashboard" style="color: #38bdf8;">/dashboard</a></p>
  </div>
</div>

<script>
const form = document.getElementById('signup-form');
const btn = document.getElementById('submit-btn');
const errorEl = document.getElementById('error-msg');
const successEl = document.getElementById('success-msg');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  btn.textContent = 'Setting up...';
  errorEl.style.display = 'none';

  const data = {
    name: document.getElementById('name').value.trim(),
    owner_name: document.getElementById('owner_name').value.trim(),
    owner_phone: document.getElementById('owner_phone').value.trim(),
    owner_email: document.getElementById('owner_email').value.trim() || null,
    service_types: document.getElementById('service_types').value.trim() || null,
  };

  try {
    const resp = await fetch('/api/v1/onboarding/signup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
    const result = await resp.json();
    if (!resp.ok) throw new Error(result.detail || 'Signup failed');

    form.style.display = 'none';
    document.getElementById('confirm-phone').textContent = data.owner_phone;
    successEl.style.display = 'block';
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Get Started — It\\'s Free';
  }
});
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def onboarding_page():
    """Serve the self-serve signup form."""
    return ONBOARDING_HTML


@router.post("/signup", response_model=BusinessOut, status_code=201)
async def signup(
    data: BusinessCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new business from the onboarding form."""
    # Check for duplicate phone
    existing = await db.execute(
        select(Business).where(Business.owner_phone == data.owner_phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A business with this phone number already exists. Contact support if you need help."
        )

    business = Business(**data.model_dump())
    db.add(business)
    await db.commit()
    await db.refresh(business)
    logger.info("New business onboarded: %s (%s)", business.name, business.owner_phone)
    return business
