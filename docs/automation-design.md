# Automation Design — Lead Hunter Squad

**Purpose:** Documentação completa de todas as automações, triggers e integrações do squad.
**Owner:** scheduler + hunter-chief
**Pattern:** PV_PM_001 (Automation Tipping Point)
**Rule:** Toda automação tem 5 guardrails obrigatórios.

---

## Automation Inventory

### Auto-Triggers Ativos

| ID | Nome | Mecanismo | Owner | Frequência |
|----|------|-----------|-------|------------|
| LH_AT_001 | WhatsApp Response Monitor | webhook + cron fallback | hunter-chief | 15 min |
| LH_AT_002 | Context Extraction Auto-Retry | event-driven | context-analyst | On failure |
| LH_AT_003 | Data Quality Review Queue | flag-based | database-manager | Continuous |
| LH_AT_004 | Archive Non-Responders | cron | database-manager | 23:00 BRT |
| LH_AT_005 | Daily Pipeline Report | cron | hunter-chief | 17:00 BRT |
| LH_AT_006 | Process Retry Queue | cron | database-manager | 08:00 BRT |
| LH_AT_007 | Cleanup Failed Retries | cron | database-manager | 23:30 BRT |
| LH_AT_008 | Handoff Trigger | event-driven | hunter-chief | On positive response |

---

## LH_AT_001: WhatsApp Response Monitor

### Design

```yaml
trigger:
  primary: "Webhook from WhatsApp API"
  fallback: "Cron every 15 minutes"
  condition: "lead_responses.processed = false"

action:
  1_classify: "Classify sentiment (positive/negative/neutral/unclear)"
  2_route:
    positive: "Execute LH_HE_004 → handoff to sales-closer"
    negative: "Update leads.status = 'closed-lost' + reason"
    neutral: "Queue for follow-up evaluation"
    unclear: "Escalate to manual review (SLA 30min)"
  3_update: "Mark response as processed"

guardrails:
  loop_prevention: "processed flag per response_id (1x only)"
  idempotency: "idempotency_key no Supabase para webhooks duplicados"
  audit_trail: "lead_responses: processed_by, processed_at, sentiment, routing_decision"
  manual_escape: "*override-response {lead_id} {decision}"
  retry_logic: "3x retry em falha de classificação → escala manual"
```

### State Transitions Triggered

```
lead.status = 'sent' + response received:
  → sentiment positive → status = 'responded' → HANDOFF
  → sentiment negative → status = 'closed-lost'
  → sentiment unclear → status = 'sent' (hold) + manual queue
```

---

## LH_AT_002: Context Extraction Auto-Retry

### Design

```yaml
trigger:
  event: "Context extraction fails for a lead"
  condition: "lead.status = 'context_pending' AND extraction_attempts < 3"

action:
  1_retry: "Re-attempt website scraping with different strategy"
  2_strategies:
    attempt_1: "Standard scrape (original URL)"
    attempt_2: "Try www. prefix / https variation"
    attempt_3: "Try Google cache or basic info only"
  3_on_success: "Update lead_context, set lead.status based on results"
  4_on_final_failure: "Flag for manual_review queue (LH_AT_003)"

guardrails:
  loop_prevention: "extraction_attempts counter (max 3)"
  idempotency: "Same lead_id never re-extracted if context exists"
  audit_trail: "extraction_log: attempt_number, strategy, result, timestamp"
  manual_escape: "*skip-context {lead_id} (proceeds without context)"
  retry_logic: "3 attempts with 5min backoff → flag for manual"
```

---

## LH_AT_003: Data Quality Review Queue

### Design

```yaml
trigger:
  event: "Lead flagged for manual review"
  sources:
    - "Extraction failed 3x (LH_AT_002)"
    - "ICP score 15-20 (borderline)"
    - "Phone format questionable"
    - "Unclear response sentiment"

action:
  1_queue: "Add to manual_review_queue table"
  2_notify: "Flag in daily report (LH_AT_005)"
  3_resolve: "Human reviews and makes decision"
  4_update: "Execute decision (approve/skip/archive)"

guardrails:
  loop_prevention: "Each lead enters queue once (unique constraint)"
  idempotency: "Resolution is final — no re-queuing"
  audit_trail: "queue_entry: reason, queued_at, resolved_by, resolution, resolved_at"
  manual_escape: "*clear-review-queue (bulk archive unresolved)"
  retry_logic: "Auto-archive if unresolved after 48h"
```

---

## LH_AT_004: Archive Non-Responders

### Design

```yaml
trigger:
  cron: "23:00 BRT daily"
  condition: "leads.status = 'sent' AND sent_at < NOW() - INTERVAL '24 hours'"

action:
  1_select: "Find all leads sent > 24h ago without response"
  2_archive: "Move to archived_leads table"
  3_queue_retry: "Add to retry_queue (scheduled for +3 business days)"
  4_update: "Set original lead status appropriately"

guardrails:
  loop_prevention: "archived_at timestamp prevents re-archiving"
  idempotency: "Archived lead_id unique constraint"
  audit_trail: "archived_leads: original_sent_at, archived_at, retry_scheduled_for"
  manual_escape: "*restore-lead {lead_id} (unarchive single lead)"
  retry_logic: "If archive fails → retry at 23:15, 23:30 → then alert"

sql: |
  -- Archive non-responders
  INSERT INTO archived_leads (lead_id, company_name, phone, original_status, archived_at)
  SELECT id, company_name, phone, status, NOW()
  FROM leads
  WHERE status = 'sent'
    AND updated_at < NOW() - INTERVAL '24 hours'
    AND id NOT IN (SELECT lead_id FROM lead_responses)
    AND id NOT IN (SELECT lead_id FROM archived_leads)
  ON CONFLICT (lead_id) DO NOTHING;
```

---

## LH_AT_005: Daily Pipeline Report

### Design

```yaml
trigger:
  cron: "17:00 BRT daily"
  condition: "At least 1 lead in pipeline"

action:
  1_collect: "Query all metrics from Supabase"
  2_evaluate: "Run pipeline-health-checklist.md"
  3_generate: "Fill pipeline-report-template.md"
  4_deliver: "Output report + flag alerts"

guardrails:
  loop_prevention: "1 report/day via idempotency_date key"
  idempotency: "Same day = same report (snapshot-based)"
  audit_trail: "daily_reports table: date, metrics_snapshot, alerts"
  manual_escape: "*pipeline-report (on-demand any time)"
  retry_logic: "Retry at 17:30 and 18:00 if initial run fails"
```

---

## LH_AT_006: Process Retry Queue

### Design

```yaml
trigger:
  cron: "08:00 BRT daily"
  condition: "retry_queue entries with scheduled_for <= TODAY"

action:
  1_select: "Get all retry-eligible leads"
  2_craft: "Create new message variation (different angle)"
  3_queue: "Add to message_queue for today's dispatch"
  4_update: "Mark retry_queue entry as processed"

guardrails:
  loop_prevention: "1 retry per lead (retry_count in retry_queue)"
  idempotency: "retry_queue.processed flag prevents double-processing"
  audit_trail: "retry_queue: original_sent_at, retry_at, new_message_id"
  manual_escape: "*cancel-retry {lead_id}"
  retry_logic: "If message craft fails → skip lead, log error"

rule: "Retry message MUST be different from original (new angle/CTA)"
```

---

## LH_AT_007: Cleanup Failed Retries

### Design

```yaml
trigger:
  cron: "23:30 BRT daily"
  condition: "retry_queue entries with retry sent > 24h ago AND no response"

action:
  1_select: "Find retried leads without response after 24h"
  2_delete: "Remove from archived_leads and retry_queue"
  3_update: "Set lead.status = 'closed-lost', reason = 'no_response_after_retry'"
  4_log: "Final cleanup logged in audit trail"

guardrails:
  loop_prevention: "cleaned_at timestamp on retry_queue entry"
  idempotency: "Cannot clean already-cleaned entries"
  audit_trail: "cleanup_log: lead_id, original_sent_at, retry_at, cleaned_at"
  manual_escape: "*preserve-lead {lead_id} (skip cleanup for specific lead)"
  retry_logic: "If cleanup fails → retry at 00:00 → then alert"
```

---

## LH_AT_008: Handoff Trigger

### Design

```yaml
trigger:
  event: "lead_responses.sentiment = 'positive' after LH_AT_001 classification"
  condition: "lead.status just changed to 'responded'"

action:
  1_assemble: "Build handoff package (handoff-package-template.md)"
  2_validate: "Run handoff-readiness-checklist.md"
  3_send: "Trigger sales-closer squad with package"
  4_update: "lead.status = 'handoff-sent'"
  5_confirm: "Wait for sales-closer confirmation (timeout 1h)"

guardrails:
  loop_prevention: "handoff_sent flag per lead (1x only)"
  idempotency: "handoff_id unique constraint"
  audit_trail: "handoffs: lead_id, package_id, sent_at, confirmed_at, destination"
  manual_escape: "*cancel-handoff {lead_id}"
  retry_logic: "If sales-closer unresponsive after 1h → escalate to human"
```

---

## Integration Architecture

### System Flow

```
Google Maps API
     ↓ (capture)
  Supabase (leads table)
     ↓ (trigger: new lead)
  Web Scraper (context extraction)
     ↓ (save context)
  Supabase (lead_context table)
     ↓ (trigger: context ready)
  LLM API (message crafting)
     ↓ (save message)
  Supabase (messages + message_queue)
     ↓ (cron: 9h-17h dispatch)
  WhatsApp API (unofficial)
     ↓ (webhook: response received)
  Supabase (lead_responses)
     ↓ (trigger: positive sentiment)
  sales-closer squad (handoff)
```

### External APIs

| API | Purpose | Auth | Rate Limit |
|-----|---------|------|------------|
| Google Maps | Lead capture | API Key | 1000 req/day (free tier) |
| Web Scraper | Context extraction | N/A | Self-hosted, no limit |
| LLM (Claude) | Message crafting | API Key | Per plan |
| WhatsApp (unofficial) | Message dispatch | Session auth | 30/hr, 200/day (self-imposed) |

### Supabase Functions (Edge Functions)

| Function | Trigger | Purpose |
|----------|---------|---------|
| `on_lead_insert` | INSERT on leads | Validate data, set initial status |
| `on_context_ready` | UPDATE lead_context | Queue for message crafting |
| `on_message_crafted` | INSERT on messages | Add to message_queue |
| `on_response_received` | INSERT on lead_responses | Classify + route |
| `enforce_lead_status_transition` | UPDATE on leads | State machine enforcement |

---

## Cron Schedule Summary

| Time (BRT) | Job | Owner |
|------------|-----|-------|
| 08:00 | Process retry queue (LH_AT_006) | database-manager |
| 09:00-17:00 | Message dispatch window | scheduler |
| 15 min intervals | Response monitor fallback (LH_AT_001) | hunter-chief |
| 17:00 | Daily pipeline report (LH_AT_005) | hunter-chief |
| 23:00 | Archive non-responders (LH_AT_004) | database-manager |
| 23:30 | Cleanup failed retries (LH_AT_007) | database-manager |

---

## Guardrails Audit

Every automation has 5 mandatory guardrails:

| Automation | Loop Prevention | Idempotency | Audit Trail | Manual Escape | Retry Logic |
|-----------|-----------------|-------------|-------------|---------------|-------------|
| LH_AT_001 | processed flag | idempotency_key | response log | *override-response | 3x → manual |
| LH_AT_002 | attempt counter | context exists check | extraction_log | *skip-context | 3x → flag |
| LH_AT_003 | unique queue entry | resolution final | queue entry | *clear-review-queue | 48h auto-archive |
| LH_AT_004 | archived_at timestamp | lead_id unique | archived_leads | *restore-lead | 3x retry → alert |
| LH_AT_005 | date key | same-day snapshot | daily_reports | *pipeline-report | 17:30, 18:00 |
| LH_AT_006 | retry_count | processed flag | retry_queue | *cancel-retry | skip + log |
| LH_AT_007 | cleaned_at timestamp | already-cleaned check | cleanup_log | *preserve-lead | 00:00 retry |
| LH_AT_008 | handoff_sent flag | handoff_id unique | handoffs table | *cancel-handoff | 1h → escalate |

**Result: 8/8 automações com 5/5 guardrails cada. Zero exceções.**

---

**Document Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Validated by:** Pedro Valério (Process Absolutist)
