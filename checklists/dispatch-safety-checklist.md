# Dispatch Safety Checklist

**Purpose:** Validate dispatch conditions before any message is sent via WhatsApp API.
**Pattern:** HO-QG-001 (Quality Gate Standard)
**Mode:** BLOCKING — dispatch HALTS if any critical check fails.
**Owner:** scheduler
**When:** Phase 5 of WF-Lead-Capture (before each message send)

---

## 1. Time Window Enforcement (HARD BLOCK)

- [ ] **Current time >= 09:00 BRT** (America/Sao_Paulo)
- [ ] **Current time <= 17:00 BRT** (America/Sao_Paulo)
- [ ] **Not a Sunday** (zero sends on Sundays)
- [ ] **Not a national holiday** (optional, configurable)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Before 09:00 BRT | HARD BLOCK — reschedule to 09:00 |
| After 17:00 BRT | HARD BLOCK — reschedule to next day 09:00 |
| Sunday | HARD BLOCK — reschedule to Monday 09:00 |

**Zero exceptions. Zero overrides.**

---

## 2. Rate Limit Enforcement (HARD BLOCK)

- [ ] **Messages this hour < 30** (max_per_hour)
- [ ] **Messages today < 200** (max_per_day)
- [ ] **Counters verified from Supabase** (not local cache)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Hourly limit reached (30) | HARD BLOCK — wait for next hour |
| Daily limit reached (200) | HARD BLOCK — wait for next day |
| Counter source = local cache | WARN — verify against Supabase |

---

## 3. Anti-Detection Measures

- [ ] **Random delay applied** (30-180 seconds between messages)
- [ ] **Delay is truly random** (not fixed interval)
- [ ] **No burst patterns** (not 30 messages then long pause)
- [ ] **Distribution across window** (spread 09:00-17:00, not all at 09:00)
- [ ] **Human-like patterns** — irregular spacing

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Fixed delay between messages | REJECT — must be randomized |
| > 10 messages in 5 minutes | HALT — too fast, adjust delays |

---

## 4. Message Pre-Send Validation

- [ ] **Lead status = 'ready'** (not already sent, not closed)
- [ ] **Message exists in messages table** for this lead
- [ ] **Message passed quality checklist** (personalization >= 7/10)
- [ ] **Phone number valid format** (+55 XX XXXXX-XXXX)
- [ ] **Lead not in closed-lost** (HARD BLOCK — zero contact)
- [ ] **Lead not already contacted today** (1 message/day/lead max)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Lead status != 'ready' | SKIP — invalid state for send |
| No message found for lead | SKIP — craft message first |
| Phone format invalid | SKIP — log error, flag for review |
| Lead is closed-lost | HARD BLOCK — LGPD compliance |
| Already contacted today | SKIP — wait 24h minimum |

---

## 5. API Health Check

- [ ] **WhatsApp API responsive** (health check before batch)
- [ ] **Authentication valid** (token not expired)
- [ ] **No ban/restriction active** (account healthy)
- [ ] **Delivery confirmations working** (can verify sent status)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| API not responding | HALT batch — retry in 5 min (max 3) |
| Auth token expired | HALT — alert for re-auth |
| Account restricted | HALT — escalate immediately |

---

## 6. Post-Send Verification

- [ ] **Message delivery confirmed** by API
- [ ] **Lead status updated** → 'sent' in Supabase
- [ ] **message_queue entry updated** (dispatched_at, status)
- [ ] **Audit trail logged** (timestamp, lead_id, message_id)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Delivery not confirmed | Re-queue with retry (max 3 attempts) |
| Supabase update failed | Retry update, log error |
| 3 failed retries | Mark as 'failed', alert hunter-chief |

---

## 7. Guardrails Summary (5 Mandatory)

| # | Guardrail | Implementation |
|---|-----------|---------------|
| 1 | **Loop Prevention** | processed flag per message_id (1x only) |
| 2 | **Idempotency** | idempotency_key no Supabase prevents double-send |
| 3 | **Audit Trail** | message_queue: dispatched_at, attempts, status |
| 4 | **Manual Escape** | `*pause-dispatch` command halts queue instantly |
| 5 | **Retry Logic** | 3x retry with exponential backoff → then fail |

---

## Pre-Batch Checklist (Run Before Every Batch)

Quick validation before starting dispatch:

1. [ ] Time window open (09:00-17:00 BRT)
2. [ ] Rate limits not exceeded (hour + day)
3. [ ] API healthy and authenticated
4. [ ] Messages in queue > 0
5. [ ] Random delays configured (30-180s)

**All 5 must PASS to start batch. Zero exceptions.**

---

**Checklist Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Phase:** WF-Lead-Capture Phase 5
