# TASKBOARD — Phase 3: Admin Portal + Notifications + Trial System

## 🎯 Goal: Admin portal, trial system, notifications, API cost tracking

## Wave 1: Foundation + Admin Portal
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #82 | All Phase 3 DB migrations (011-015) | Backend | 🔄 IN PROGRESS |
| #83 | Admin auth middleware + superadmin role + seed script | Backend | ⏳ Blocked by #82 |
| #84 | Admin dashboard — analytics, revenue, MRR | Backend + Frontend | ✅ Frontend PR#108 — awaiting Backend endpoints |
| #85 | Admin user management | Backend + Frontend | ✅ Frontend PR#108 — awaiting Backend endpoints |
| #86 | Admin trial monitor | Backend + Frontend | ✅ Frontend PR#108 — awaiting Backend endpoints |

## Wave 2: Trial + Notifications
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #87 | 14-day free trial system | Backend + Frontend | 🔲 |
| #88 | Trial usage limits + grace period | Backend + Frontend | 🔲 |
| #89 | Notification system + bell icon | Backend + Frontend | 🔲 |
| #90 | Auto-notifications + admin broadcast | Backend | 🔲 |
| #91 | FCM token registration + push stub | Backend | 🔲 |

## Wave 3: API Usage Tracking
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #92 | API usage logging middleware | Backend | 🔲 |
| #93 | Admin usage dashboard + margin calc | Backend + Frontend | 🔲 |

## Wave 4A: Core Enhancements
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #94 | Audit log | Backend | 🔲 |
| #95 | RBAC + user impersonation | Backend | 🔲 |
| #96 | Integration health page | Backend + Frontend | 🔲 |
| #97 | Onboarding tracking + analytics funnel | Backend + Frontend | 🔲 |

## Wave 4B-1: Backend-only
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #98 | Automated churn alerts | Backend | 🔲 |
| #100 | API rate limiting per plan | Backend | 🔲 |
| #101 | Brute force protection | Backend | 🔲 |
| #103 | Webhook retry queue | Backend | 🔲 |

## Wave 4B-2: Frontend
| Issue | Title | Agent | Status |
|-------|-------|-------|--------|
| #99 | Email template customization | Backend + Frontend | 🔲 |
| #102 | Session management | Backend + Frontend | 🔲 |
| #104 | CSV/PDF export | Backend + Frontend | 🔲 |

## Rules
- QA pass + auto-deploy health 200 BEFORE next wave starts
- Backend creates ALL migrations — no parallel
- Merge order: migrations → middleware → features
- Pre-commit checklist on every PR
- Max 40k tokens per agent session (QA: 30k)
