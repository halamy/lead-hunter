# Handoff Readiness Checklist

**Purpose:** Validate handoff package completeness before sending lead to sales-closer squad.
**Pattern:** HO-QG-001 (Quality Gate Standard)
**Mode:** BLOCKING — incomplete handoff packages are BLOCKED.
**Owner:** hunter-chief
**When:** Phase 6 of WF-Lead-Capture (when lead responds positively)

---

## 1. Response Validation

- [ ] **Response received** and stored in `lead_responses` table
- [ ] **Sentiment classified** (positive, negative, neutral, unclear)
- [ ] **Sentiment = positive** (interested, wants_more_info, question)
- [ ] **Classification confidence** logged
- [ ] **Response text** captured verbatim

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Sentiment = negative | BLOCK handoff — mark closed-lost |
| Sentiment = unclear | HOLD — manual review queue (SLA 30min) |
| No response text | BLOCK — cannot hand off without content |

---

## 2. Lead Profile (Required Fields)

- [ ] **company_name** — Business name from Google Maps
- [ ] **phone** — Valid phone number (+55 format)
- [ ] **website** — URL (if available)
- [ ] **address** — Physical address from Google Maps
- [ ] **icp_score** — Qualification score (>= 21/30)
- [ ] **status** — Must be 'responded'

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Missing company_name | BLOCK — basic data required |
| Missing phone | BLOCK — sales-closer needs contact |
| ICP score < 21/30 | WARN — flag as low-quality lead |
| Status != 'responded' | BLOCK — invalid state for handoff |

---

## 3. Context Summary (Required)

- [ ] **Pain points identified** (minimum 1, ideal 2+)
- [ ] **Services offered** by the lead's company
- [ ] **Company size indicator** (employees, locations, revenue signals)
- [ ] **Tech stack** (if available)
- [ ] **Urgency signals** (hiring, expanding, complaints)
- [ ] **Context confidence score** >= 5/10

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Zero pain points | WARN — sales-closer needs ammunition |
| No services identified | WARN — less context for closer |
| Confidence < 3/10 | BLOCK — context unreliable |

---

## 4. Conversation History

- [ ] **First message sent** (our outreach message)
- [ ] **First message text** included
- [ ] **Response received** (their reply)
- [ ] **Response text** included
- [ ] **Timestamps** for both (sent_at, responded_at)
- [ ] **Time to response** calculated

### Veto Conditions

| Condition | Action |
|-----------|--------|
| No outreach message in package | BLOCK — closer needs conversation context |
| No response text | BLOCK — closer needs to see what was said |

---

## 5. Handoff Package Assembly

### Required Package Contents

```yaml
handoff_package:
  lead_profile:
    company_name: "{string}"      # REQUIRED
    phone: "{string}"             # REQUIRED
    website: "{string|null}"      # OPTIONAL
    address: "{string}"           # REQUIRED
    icp_score: "{number}"         # REQUIRED
    google_maps_rating: "{number|null}"  # OPTIONAL

  context_summary:
    pain_points: ["{string}"]     # REQUIRED (min 1)
    services_offered: ["{string}"] # REQUIRED
    company_size: "{string}"      # OPTIONAL
    tech_stack: ["{string}"]      # OPTIONAL
    urgency_signals: ["{string}"] # OPTIONAL
    confidence_score: "{number}"  # REQUIRED

  conversation:
    outreach_message: "{string}"  # REQUIRED
    outreach_sent_at: "{datetime}" # REQUIRED
    response_text: "{string}"     # REQUIRED
    response_received_at: "{datetime}" # REQUIRED
    sentiment: "{string}"         # REQUIRED
    time_to_response: "{duration}" # REQUIRED

  qualification:
    icp_score: "{number}"         # REQUIRED
    personalization_score: "{number}" # REQUIRED
    response_sentiment: "{string}" # REQUIRED
    recommended_approach: "{string}" # OPTIONAL
```

### Package Completeness Scoring

| Required Fields Present | Score | Status |
|------------------------|-------|--------|
| 12/12 | 100% | PASS — hand off immediately |
| 10-11/12 | 83-92% | CONDITIONAL — hand off with note |
| < 10/12 | < 83% | BLOCK — complete package first |

---

## 6. Handoff Execution

- [ ] **Package validated** against this checklist
- [ ] **sales-closer squad notified** (trigger event)
- [ ] **Lead status updated** in Supabase (responded → handoff-pending)
- [ ] **Handoff logged** in audit trail (timestamp, package_id, destination)
- [ ] **Confirmation received** from sales-closer (package accepted)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Package validation failed | BLOCK — fix package first |
| sales-closer squad unavailable | QUEUE — retry in 15 min (max 5) |
| No confirmation after 1 hour | ESCALATE to human |

---

## Quick Validation (5 Critical Checks)

Before executing handoff, verify:

1. [ ] Sentiment = positive (not negative/unclear)
2. [ ] Lead profile has company_name + phone
3. [ ] Context has >= 1 pain point
4. [ ] Conversation has outreach + response texts
5. [ ] ICP score >= 21/30

**All 5 must PASS. Zero exceptions.**

---

**Checklist Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Phase:** WF-Lead-Capture Phase 6
**Destination:** sales-closer squad
