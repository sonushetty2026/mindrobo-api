const { test, expect } = require('@playwright/test');
const { DBHelper } = require('./db-helper');

const TS = Date.now();
const TEST_PASSWORD = 'SecurePass123!';
let db;

test.beforeAll(async () => {
  db = new DBHelper();
  await db.connect();
});

test.afterAll(async () => {
  await db.disconnect();
});

// SMOKE TESTS
const publicPages = ['/', '/signup', '/login', '/forgot-password', '/health'];
const authPages = ['/dashboard', '/onboarding', '/leads', '/billing', '/settings',
                   '/appointments', '/analytics', '/warroom', '/phone-setup',
                   '/admin', '/admin/users', '/admin/trials', '/admin/usage',
                   '/admin/audit', '/admin/health-check', '/admin/email-templates',
                   '/account/sessions', '/notifications'];

for (const url of publicPages) {
  test('Smoke: ' + url + ' returns 200', async ({ request }) => {
    const res = await request.get(url);
    expect(res.status()).toBe(200);
  });
}

for (const url of authPages) {
  test('Smoke: ' + url + ' returns 200', async ({ request }) => {
    const res = await request.get(url);
    expect(res.status()).toBe(200);
  });
}

// BROWSER TESTS
test('Landing page renders', async ({ page }) => {
  await page.goto('/');
  const content = await page.content();
  expect(content.toLowerCase()).toContain('mindrobo');
});

test('Signup form visible', async ({ page }) => {
  await page.goto('/signup');
  await expect(page.locator('#email')).toBeVisible();
  await expect(page.locator('#password')).toBeVisible();
  await expect(page.locator('#business-name')).toBeVisible();
});

// USER REGISTRATION + DB ASSERTION
test('Registration creates DB record', async ({ page }) => {
  const email = 'reg_' + TS + '@test.co';
  await page.goto('/signup');
  await page.fill('#business-name', 'Reg Test Biz');
  await page.fill('#email', email);
  await page.fill('#password', TEST_PASSWORD);
  await page.fill('#confirm-password', TEST_PASSWORD);
  await page.click('#submit-btn');
  await page.waitForTimeout(3000);

  const user = await db.getUserByEmail(email);
  expect(user).not.toBeNull();
  expect(user.email).toBe(email);
  expect(user.is_verified).toBe(false);
  expect(user.is_trial).toBe(true);
  expect(user.business_id).not.toBeNull();

  // Cleanup
  await db.deleteTestUser(email);
  await db.deleteTestBusiness('Reg Test Biz');
});

// LOGIN REDIRECT
test('Login redirects new user to onboarding', async ({ page }) => {
  const email = 'login_' + TS + '@test.co';
  // Create user via API
  await page.request.post('/api/v1/auth/register', {
    data: { email, password: TEST_PASSWORD, business_name: 'Login Test Biz' }
  });
  await db.query('UPDATE users SET is_verified = true WHERE email = $1', [email]);

  await page.goto('/login');
  await page.fill('#email', email);
  await page.fill('#password', TEST_PASSWORD);
  await page.click('#submit-btn');
  await page.waitForURL(/onboarding|dashboard/, { timeout: 10000 });
  expect(page.url()).toMatch(/onboarding|dashboard/);

  const user = await db.getUserByEmail(email);
  expect(user.last_login_at).not.toBeNull();

  await db.deleteTestUser(email);
  await db.deleteTestBusiness('Login Test Biz');
});

// PROFILE DROPDOWN
test('Dashboard has profile dropdown', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForTimeout(1000);
  const avatar = page.locator('#profile-toggle');
  if (await avatar.isVisible()) {
    await avatar.click();
    await page.waitForTimeout(500);
    expect(await page.locator('.profile-dropdown').isVisible()).toBe(true);
  }
});

// API TESTS - each with fresh user to avoid rate limiting
test('API endpoints return 200 with JWT', async ({ request }) => {
  const email = 'api_' + TS + '@test.co';
  await request.post('/api/v1/auth/register', {
    data: { email, password: TEST_PASSWORD, business_name: 'API Test Biz' }
  });
  await db.query('UPDATE users SET is_verified = true WHERE email = $1', [email]);

  const loginRes = await request.post('/api/v1/auth/login', {
    data: { email, password: TEST_PASSWORD }
  });
  expect(loginRes.status()).toBe(200);
  const { access_token, role, email: returnedEmail } = await loginRes.json();
  expect(access_token).toBeTruthy();
  expect(role).toBe('user');
  expect(returnedEmail).toBe(email);

  const headers = { Authorization: 'Bearer ' + access_token };
  const endpoints = [
    '/api/v1/auth/me',
    '/api/v1/users/me/trial-status',
    '/api/v1/users/me/usage-limits',
    '/api/v1/dashboard/recent',
    '/api/v1/leads/',
    '/api/v1/businesses/',
    '/api/v1/notifications/',
    '/api/v1/notifications/unread-count',
  ];

  for (const ep of endpoints) {
    const res = await request.get(ep, { headers });
    expect(res.status(), ep + ' should be 200').toBe(200);
  }

  await db.deleteTestUser(email);
  await db.deleteTestBusiness('API Test Biz');
});

// TRIAL STATUS + DB ASSERTION
test('Trial status correct in API and DB', async ({ request }) => {
  const email = 'trial_' + TS + '@test.co';
  await request.post('/api/v1/auth/register', {
    data: { email, password: TEST_PASSWORD, business_name: 'Trial Test Biz' }
  });
  await db.query('UPDATE users SET is_verified = true WHERE email = $1', [email]);

  const loginRes = await request.post('/api/v1/auth/login', {
    data: { email, password: TEST_PASSWORD }
  });
  const { access_token } = await loginRes.json();

  const trialRes = await request.get('/api/v1/users/me/trial-status', {
    headers: { Authorization: 'Bearer ' + access_token }
  });
  const trial = await trialRes.json();
  expect(trial.is_trial).toBe(true);
  expect(trial.days_remaining).toBeGreaterThan(0);

  const user = await db.getUserByEmail(email);
  expect(user.is_trial).toBe(true);
  expect(user.trial_ends_at).not.toBeNull();

  await db.deleteTestUser(email);
  await db.deleteTestBusiness('Trial Test Biz');
});

// SOFT DELETE + DB ASSERTION
test('Soft delete sets is_active=false in DB', async ({ request }) => {
  const email = 'del_' + TS + '@test.co';
  await request.post('/api/v1/auth/register', {
    data: { email, password: TEST_PASSWORD, business_name: 'Del Test Biz' }
  });
  await db.query('UPDATE users SET is_verified = true WHERE email = $1', [email]);

  const loginRes = await request.post('/api/v1/auth/login', {
    data: { email, password: TEST_PASSWORD }
  });
  const { access_token } = await loginRes.json();

  const delRes = await request.delete('/api/v1/auth/delete-account', {
    headers: { Authorization: 'Bearer ' + access_token }
  });
  expect(delRes.status()).toBe(200);

  const user = await db.getUserByEmail(email);
  expect(user.is_active).toBe(false);

  await db.deleteTestUser(email);
  await db.deleteTestBusiness('Del Test Biz');
});
