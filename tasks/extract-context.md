# Extract Context

**Task ID:** `extract-context`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Extract Context |
| **status** | `pending` |
| **responsible_executor** | context-analyst |
| **execution_type** | `Agent` |
| **input** | leads with websites from Supabase |
| **output** | lead_context table populated with intelligence |
| **action_items** | 5 steps |
| **acceptance_criteria** | 4 criteria |

## Overview

Scrape and analyze lead websites to extract actionable intelligence for message personalization. Identify services, pain points, company size, and tech stack.

## Input

- **leads** (array)
  - Description: Leads with website URLs from Supabase
  - Required: Yes
  - Source: Supabase `leads` table where status = 'new' AND website IS NOT NULL

## Output

- **lead_context** (array)
  - Description: Context records with extracted intelligence
  - Destination: Supabase `lead_context` table
  - Format: `{lead_id, services, pain_points, company_size, tech_stack, context_score}`

## Action Items

### Step 1: Fetch Leads with Websites
Query Supabase for leads with status = 'new' and non-null website.

### Step 2: Scrape Website
For each lead: scan homepage, services page, about page, contact page.

### Step 3: Extract Intelligence
Identify: services offered, target audience, pain signals, company size indicators, tech stack.

### Step 4: Score Context Quality
Rate 1-10 based on: completeness of data, pain points found, specificity.

### Step 5: Store & Update Status
Save to lead_context table. Update lead status to 'context_pending' → 'ready'.

## Acceptance Criteria

- [ ] **AC-1:** Context extracted for >= 80% of leads with websites
- [ ] **AC-2:** At least 1 pain point identified per lead
- [ ] **AC-3:** Context score >= 5/10 for usable leads
- [ ] **AC-4:** Failed extractions queued for retry (LH_AT_002 watchdog, max 3 retries)

## Veto Conditions

- **Extraction rate < 50%** → PAUSE — investigate scraping failures
- **Lead without website** → SKIP context, proceed with basic info only
- **Website blocked/timeout** → Queue for retry, max 3 attempts

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Task** | `craft-message` |
| **Trigger** | Context saved to Supabase |
| **Executor** | message-crafter |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
