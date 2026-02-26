# Qualify Lead

**Task ID:** `qualify-lead`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Qualify Lead |
| **status** | `pending` |
| **responsible_executor** | lead-qualifier |
| **execution_type** | `Agent` |
| **input** | ICP parameters (industry, size, location, budget indicators) |
| **output** | ICP scoring criteria, qualification thresholds, search query |
| **action_items** | 5 steps |
| **acceptance_criteria** | 4 criteria |

## Overview

Define Ideal Customer Profile criteria and scoring framework before lead capture begins. This task gates the entire pipeline — no leads enter without passing the 30-point ICP scoring.

## Input

- **icp_parameters** (object)
  - Description: Target customer dimensions (industry, company_size, location, services)
  - Required: Yes
  - Source: User input or campaign definition

- **campaign_context** (string)
  - Description: What product/service is being sold
  - Required: Yes
  - Source: User input

## Output

- **icp_definition** (object)
  - Description: Complete ICP with scoring weights per dimension
  - Destination: Session context + Supabase config

- **search_query** (string)
  - Description: Google Maps search query derived from ICP
  - Format: "{industry} {location}"

- **qualification_threshold** (number)
  - Description: Minimum score to proceed (default: 21/30)

## Action Items

### Step 1: Gather ICP Dimensions
Elicit from user: target industry, company size, geographic location, budget indicators, tech signals.

### Step 2: Define Scoring Framework
Apply 30-point scoring across 6 dimensions (5 points each):
- Industry fit
- Company size
- Location match
- Online presence
- Service alignment
- Growth indicators

### Step 3: Set Qualification Threshold
Default: >= 21/30 (70%). User can adjust.

### Step 4: Formulate Search Query
Transform ICP into Google Maps search: `"{industry}" "{city}, {state}"`.

### Step 5: Define Disqualification Rules
Hard blocks:
- No phone number → auto-disqualify
- Competitor → auto-disqualify
- Already in database → skip

## Acceptance Criteria

- [ ] **AC-1:** ICP covers minimum 3 dimensions with scoring weights
- [ ] **AC-2:** Qualification threshold defined and documented
- [ ] **AC-3:** Search query formulated and validated
- [ ] **AC-4:** Disqualification rules cover edge cases

## Veto Conditions

- **No ICP dimensions defined** → BLOCK — cannot proceed to capture
- **Threshold < 15/30** → WARN — too permissive, recommend >= 21
- **Search query too broad** (e.g., just city name) → BLOCK — refine required

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Task** | `capture-leads` |
| **Trigger** | ICP definition approved |
| **Executor** | google-maps-hunter |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
