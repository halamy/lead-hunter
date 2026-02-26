# Capture Leads

**Task ID:** `capture-leads`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Capture Leads |
| **status** | `pending` |
| **responsible_executor** | google-maps-hunter |
| **execution_type** | `Agent` |
| **input** | search_query, quantity, ICP criteria |
| **output** | leads in Supabase with status = 'new' |
| **action_items** | 5 steps |
| **acceptance_criteria** | 5 criteria |

## Overview

Execute Google Maps search and capture business leads matching ICP criteria. Extract: name, phone, website, address, rating. Apply data quality gates before storing.

## Input

- **search_query** (string)
  - Description: Google Maps search query from qualify-lead task
  - Required: Yes
  - Source: qualify-lead output

- **quantity** (number)
  - Description: Target number of leads to capture
  - Required: Yes
  - Source: User input (default: 50)

- **icp_criteria** (object)
  - Description: Scoring framework for qualification
  - Required: Yes
  - Source: qualify-lead output

## Output

- **captured_leads** (array)
  - Description: Leads saved to Supabase leads table
  - Destination: Supabase `leads` table
  - Format: `{name, phone, website, address, rating, status: 'new'}`

- **capture_report** (object)
  - Description: Summary of capture results
  - Format: `{total_found, total_qualified, total_skipped, skip_reasons}`

## Action Items

### Step 1: Execute Google Maps Search
Run search query. Paginate through results up to target quantity.

### Step 2: Extract Lead Data
For each result extract: business_name, phone, website, address, rating, category.

### Step 3: Apply Quality Gate GMH_001
- Phone number required → skip if missing
- Heuristic GMH_002: Prioritize leads with website (website = higher context potential)

### Step 4: Deduplicate (GMH_003)
Check Supabase for existing phone numbers. Skip duplicates.

### Step 5: Store in Supabase
Insert qualified leads with `status = 'new'`. Log capture_report.

## Acceptance Criteria

- [ ] **AC-1:** All captured leads have phone number (GMH_001 enforced)
- [ ] **AC-2:** Duplicates removed before insertion (GMH_003)
- [ ] **AC-3:** Leads saved to Supabase with status = 'new'
- [ ] **AC-4:** Capture report generated with totals
- [ ] **AC-5:** At least 1 lead captured (otherwise pipeline halts)

## Veto Conditions

- **0 leads captured** → HALT pipeline, review search query
- **> 50% skip rate** → WARN — ICP may be too restrictive
- **Duplicate rate > 30%** → WARN — query overlaps with previous campaigns

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Task** | `extract-context` |
| **Trigger** | Leads saved to Supabase |
| **Executor** | context-analyst |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
