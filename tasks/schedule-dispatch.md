# Schedule Dispatch

**Task ID:** `schedule-dispatch`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Schedule Dispatch |
| **status** | `pending` |
| **responsible_executor** | scheduler |
| **execution_type** | `Worker` |
| **input** | message_queue entries from Supabase |
| **output** | messages sent via WhatsApp, lead status updated |
| **action_items** | 5 steps |
| **acceptance_criteria** | 5 criteria |

## Overview

Process message queue and dispatch via WhatsApp API within business hours (9h-17h BRT). Enforce rate limits (30/hr, 200/day) and apply random delays (30-180s) for anti-detection.

## Input

- **message_queue** (array)
  - Description: Scheduled messages pending dispatch
  - Required: Yes
  - Source: Supabase `message_queue` WHERE status = 'scheduled'

## Output

- **dispatch_report** (object)
  - Description: Summary of sent/failed/pending messages
  - Format: `{total_sent, total_failed, total_pending, rate_used}`

## Action Items

### Step 1: Check Time Window
Verify current time is within 9h-17h BRT. If outside, calculate next window start.

### Step 2: Check Rate Limits
Query today's sent count. Verify < 200/day and current hour < 30/hr.

### Step 3: Process Queue
For each queued message:
- Send via WhatsApp API
- Apply random delay (30-180s)
- Update message status: scheduled → sent
- Update lead status: ready → sent

### Step 4: Handle Failures
Failed sends → retry queue (max 3 attempts with exponential backoff).

### Step 5: Generate Dispatch Report
Log: total_sent, total_failed, remaining_in_queue, rate_utilization.

## Acceptance Criteria

- [ ] **AC-1:** No messages sent outside 9h-17h BRT
- [ ] **AC-2:** Rate limits respected (30/hr, 200/day)
- [ ] **AC-3:** Random delays applied between messages (30-180s)
- [ ] **AC-4:** Lead status updated to 'sent' in Supabase
- [ ] **AC-5:** Failed sends queued for retry

## Veto Conditions

- **Outside time window** → HALT — wait for next 9h window
- **Rate limit reached (hourly)** → PAUSE — resume next hour
- **Rate limit reached (daily)** → HALT — resume tomorrow 9h
- **WhatsApp API error** → Retry 3x, then flag for manual intervention

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Task** | `process-responses` |
| **Trigger** | Messages dispatched |
| **Executor** | hunter-chief |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
