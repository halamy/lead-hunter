# Pipeline Report

**Task ID:** `pipeline-report`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Pipeline Report |
| **status** | `pending` |
| **responsible_executor** | hunter-chief |
| **execution_type** | `Worker` |
| **input** | Supabase pipeline data |
| **output** | Daily pipeline metrics summary |
| **action_items** | 4 steps |
| **acceptance_criteria** | 3 criteria |

## Overview

Generate daily pipeline report with key metrics. Auto-triggered at 17h BRT (LH_AT_005). Summarizes: leads captured, messages sent, responses received, handoffs made, conversion rates.

## Input

- **pipeline_data** (object)
  - Description: Aggregated data from all pipeline tables
  - Required: Yes
  - Source: Supabase views (pipeline_overview, todays_activity)

## Output

- **pipeline_report** (object)
  - Description: Daily metrics summary
  - Format: Structured report with KPIs

## Action Items

### Step 1: Query Pipeline Metrics
Fetch from Supabase views: pipeline_overview, todays_activity.

### Step 2: Calculate KPIs
- Leads captured today
- Messages sent today
- Response rate (responses / messages_sent)
- Handoff rate (handoffs / responses)
- Pipeline conversion (handoffs / leads_captured)

### Step 3: Identify Bottlenecks
Flag stages with below-average conversion:
- < 80% context extraction rate
- < 5% response rate
- < 50% handoff rate from responses

### Step 4: Generate Report
Format metrics as structured summary with trends vs previous day.

## Acceptance Criteria

- [ ] **AC-1:** All KPIs calculated and presented
- [ ] **AC-2:** Bottlenecks identified with specific recommendations
- [ ] **AC-3:** Report generated within 5 minutes of trigger

## Veto Conditions

- **No data for today** → SKIP — no activity to report
- **Supabase connection failure** → RETRY 3x, then notify user

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
