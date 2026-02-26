# Process Responses

**Task ID:** `process-responses`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Process Responses |
| **status** | `pending` |
| **responsible_executor** | hunter-chief |
| **execution_type** | `Agent` |
| **input** | WhatsApp responses from lead_responses table |
| **output** | classified responses, handoff packages for sales-closer |
| **action_items** | 5 steps |
| **acceptance_criteria** | 4 criteria |

## Overview

Monitor and classify incoming WhatsApp responses. Route positive responses to sales-closer squad via handoff. Classify: positive, negative, question, neutral. Build handoff packages with lead context.

## Input

- **responses** (array)
  - Description: Incoming WhatsApp messages from leads
  - Required: Yes
  - Source: Supabase `lead_responses` WHERE classified = false

## Output

- **classified_responses** (array)
  - Description: Responses with sentiment classification
  - Destination: Supabase `lead_responses` updated

- **handoff_packages** (array)
  - Description: Complete packages for positive leads → sales-closer
  - Format: `{lead_profile, context_summary, response, qualification_score}`

## Action Items

### Step 1: Fetch Unclassified Responses
Query lead_responses for new/unclassified entries.

### Step 2: Classify Sentiment (LH_HE_001)
Analyze response content:
- **Positive:** Interest, questions about service, wants to know more
- **Negative:** Not interested, stop contacting, explicit rejection
- **Question:** Asks about pricing, process, timelines
- **Neutral:** Unclear intent, acknowledgment only

### Step 3: Route Positive Responses
For positive/question classifications:
- Build handoff package (lead_profile + context_summary + response + score)
- Trigger handoff to sales-closer squad
- Update lead status: sent → responded

### Step 4: Handle Negative Responses
- Update lead status: sent → closed-disqualified
- No further contact
- Log rejection reason

### Step 5: Archive Neutrals
- Queue for follow-up if unclear
- Update status: sent → follow_up_pending

## Acceptance Criteria

- [ ] **AC-1:** All responses classified within 2 hours of receipt
- [ ] **AC-2:** Positive leads handed off with complete package
- [ ] **AC-3:** Negative leads closed immediately (no further contact)
- [ ] **AC-4:** Handoff package includes all 4 required fields

## Veto Conditions

- **Incomplete handoff package** → BLOCK handoff — complete data first
- **Negative response classified as positive** → CRITICAL — misclassification
- **Lead already in sales-closer** → SKIP — avoid duplicate handoff

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Squad** | `sales-closer` |
| **Trigger** | Positive response classified |
| **Executor** | closer-chief |
| **Package** | lead_profile, context_summary, response, qualification_score |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
