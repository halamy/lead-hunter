# Lead Hunter - Database Migrations

## 001_p0_veto_enforcement.sql

**Author:** Pedro Valerio (Process Absolutist)
**Date:** 2026-02-24
**Status:** Ready to apply

### What it fixes

| # | Problem | Fix | Type |
|---|---------|-----|------|
| P0-1 | State machine has no transition enforcement | `enforce_lead_status_transition()` trigger | PHYSICAL BLOCK |
| P0-1b | Message status can go backward | `enforce_message_status_transition()` trigger | PHYSICAL BLOCK |
| P0-2 | No automated handoff to sales-closer | `handoff_queue` table + auto-trigger on `responded` | AUTOMATION |
| P0-2b | No rejection return path from gatekeeper | `handoff_rejections` table | AUTOMATION |
| P0-3 | Duplicate phones allowed | `UNIQUE INDEX` on `leads.phone` (active only) | PHYSICAL BLOCK |
| P0-4 | Rate limits are documentation only | `rate_limit_log` + `check_rate_limit()` + triggers | PHYSICAL BLOCK |
| P0-4b | Business hours not enforced | `enforce_business_hours_on_queue()` trigger | PHYSICAL BLOCK |
| P0-6 | ICP score mismatch (1-10 vs 1-30) | ALTER CHECK to 1-30 + `icp_dimensions` JSONB | ALIGNMENT |
| P0-6b | ICP threshold not enforced | `enforce_icp_threshold()` trigger (>= 21/30) | PHYSICAL BLOCK |
| P0-6c | `context_retry_count` missing from schema | ADD COLUMN `context_retry_count` | FIX |
| Bonus | Personalization minimum not enforced | `enforce_personalization_minimum()` trigger (>= 5/10) | PHYSICAL BLOCK |

### How to apply

```sql
-- In Supabase SQL Editor or psql:
\i data/migrations/001_p0_veto_enforcement.sql
```

### New tables

- `handoff_queue` - Bridge between lead-hunter and sales-closer
- `handoff_rejections` - Return path from sales-closer gatekeeper
- `rate_limit_log` - Rate limiting enforcement

### New functions

- `enforce_lead_status_transition()` - State machine guard
- `enforce_message_status_transition()` - Message state guard
- `auto_create_handoff_on_response()` - Auto-populate handoff queue
- `check_rate_limit()` - Rate limit checker (call before send)
- `log_rate_limit_action()` - Log successful send
- `enforce_rate_limit_on_queue()` - Block queue if limit exceeded
- `enforce_business_hours_on_queue()` - Block sends outside 9h-17h BRT
- `enforce_icp_threshold()` - Block unqualified leads
- `enforce_personalization_minimum()` - Block low-quality messages

### Breaking changes

- `leads.icp_score` now CHECK (1-30) instead of (1-10). Update scoring logic.
- `leads.status` now includes: `context_failed`, `delivered`, `read`, `failed`.
- Invalid status transitions will raise exceptions. Update agent code accordingly.
