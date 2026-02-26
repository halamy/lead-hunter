# Pipeline Health Checklist

**Purpose:** Daily validation of lead pipeline health and squad performance.
**Pattern:** HO-QG-001 (Quality Gate Standard)
**Mode:** ADVISORY — flags issues, does not block (runs daily at 17:00 BRT).
**Owner:** hunter-chief
**When:** Daily via auto-trigger LH_AT_005

---

## 1. Lead Flow Metrics

- [ ] **Leads captured today** > 0 (if campaign active)
- [ ] **Context extraction rate** >= 80%
- [ ] **Messages crafted** for all leads with context
- [ ] **Messages sent** within rate limits
- [ ] **Zero leads stuck** in intermediate states > 24h

### Health Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Capture rate | >= target/day | 50-99% of target | < 50% of target |
| Context extraction | >= 80% | 60-79% | < 60% |
| Message craft rate | >= 90% of contexted | 70-89% | < 70% |
| Dispatch rate | >= 90% of crafted | 70-89% | < 70% |
| Response rate | >= 5% | 2-4% | < 2% |

---

## 2. State Machine Integrity

- [ ] **No orphaned leads** (status = NULL or unknown)
- [ ] **No backward transitions** detected in logs
- [ ] **All leads have valid status** from enum
- [ ] **closed-lost leads** have `closed_reason` populated

### Validation Query

```sql
-- Orphaned leads (invalid status)
SELECT COUNT(*) FROM leads
WHERE status NOT IN ('new', 'context_pending', 'ready', 'sent', 'responded', 'closed-lost');

-- Stuck leads (> 24h in same status)
SELECT id, company_name, status, updated_at
FROM leads
WHERE updated_at < NOW() - INTERVAL '24 hours'
  AND status NOT IN ('responded', 'closed-lost');
```

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Orphaned leads found | ALERT — investigate and fix |
| Backward transition detected | ESCALATE — database trigger may be broken |
| Stuck leads > 10% | WARN — check pipeline bottleneck |

---

## 3. Rate Limit Compliance

- [ ] **Never exceeded 30/hour** in last 24h
- [ ] **Never exceeded 200/day** in last 24h
- [ ] **No sends outside 9h-17h** in last 24h
- [ ] **Random delays applied** (avg delay between 30-180s)

### Validation Query

```sql
-- Rate limit violations (hourly)
SELECT date_trunc('hour', sent_at) as hour, COUNT(*)
FROM messages WHERE sent_at > NOW() - INTERVAL '24 hours'
  AND status = 'sent'
GROUP BY hour HAVING COUNT(*) > 30;

-- Time window violations
SELECT COUNT(*) FROM messages
WHERE sent_at > NOW() - INTERVAL '24 hours'
  AND status = 'sent'
  AND (EXTRACT(HOUR FROM sent_at AT TIME ZONE 'America/Sao_Paulo') < 9
    OR EXTRACT(HOUR FROM sent_at AT TIME ZONE 'America/Sao_Paulo') >= 17);
```

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Hourly limit exceeded | CRITICAL — investigate scheduler bug |
| Time window violation | CRITICAL — halt dispatch, audit |
| Average delay < 30s | WARN — increase randomization |

---

## 4. Response Monitoring

- [ ] **All responses classified** within 2 hours
- [ ] **Positive responses** handed off to sales-closer
- [ ] **Negative responses** marked closed-lost with reason
- [ ] **Unclear responses** in manual review queue (SLA 30min)
- [ ] **No unprocessed responses** older than 4 hours

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Unprocessed response > 4h | ALERT — potential missed opportunity |
| Positive response not handed off | ESCALATE — revenue impact |
| Unclear in queue > 30min | AUTO-ARCHIVE per LH_HE_004 |

---

## 5. Data Cleanup Status

- [ ] **archive_non_responders** ran at 23:00 BRT (cron)
- [ ] **process_retry_queue** ran at 08:00 BRT (cron)
- [ ] **cleanup_failed_retries** ran at 23:30 BRT (cron)
- [ ] **Archived leads count** is reasonable (not growing indefinitely)
- [ ] **retry_queue** processing normally

---

## 6. Handoff Quality

- [ ] **All handoff packages complete** (profile + context + response + score)
- [ ] **Zero incomplete handoffs** sent to sales-closer
- [ ] **Handoff latency** < 30 minutes from response to handoff

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Incomplete handoff package | BLOCK handoff — complete first |
| Handoff latency > 1 hour | WARN — speed up processing |

---

## Daily Report Template

```
Pipeline Health Report — {DATE}

LEADS
- Captured: {N} | Target: {T} | {%}
- Context extracted: {N}/{total} ({%})
- Messages crafted: {N}
- Messages sent: {N}
- Responses: {N} ({response_rate}%)

HANDOFFS
- To sales-closer: {N}
- Pending: {N}

COMPLIANCE
- Rate limit violations: {N}
- Time window violations: {N}
- Avg delay between messages: {N}s

HEALTH
- Stuck leads: {N}
- Unprocessed responses: {N}
- Failed dispatches: {N}

STATUS: {HEALTHY | WARNING | CRITICAL}
```

---

## Escalation Matrix

| Severity | Trigger | Action |
|----------|---------|--------|
| INFO | Metrics within thresholds | Log only |
| WARNING | 1+ warnings in report | Alert hunter-chief |
| CRITICAL | Any rate limit or time window violation | Halt dispatch + alert |
| EMERGENCY | Account restriction or API ban | Full stop + escalate to human |

---

**Checklist Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Trigger:** Daily at 17:00 BRT (LH_AT_005)
