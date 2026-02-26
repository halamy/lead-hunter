# Craft Message

**Task ID:** `craft-message`
**Pattern:** HO-TP-001 (Task Anatomy Standard)
**Version:** 1.0.0
**Last Updated:** 2026-02-19

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Craft Message |
| **status** | `pending` |
| **responsible_executor** | message-crafter |
| **execution_type** | `Agent` |
| **input** | lead profile + lead_context from Supabase |
| **output** | personalized messages in messages table, entries in message_queue |
| **action_items** | 5 steps |
| **acceptance_criteria** | 4 criteria |

## Overview

Create personalized WhatsApp first-touch messages using lead context. Apply Value Equation (Hormozi) for value framing and Direct Response (Halbert) for compelling copy. Each message must reference specific context from the lead's website.

## Input

- **lead_with_context** (object)
  - Description: Lead profile + extracted context
  - Required: Yes
  - Source: Supabase `leads` JOIN `lead_context`

- **message_template_style** (string)
  - Description: Tone/style preference (casual, professional, hybrid)
  - Required: No
  - Source: Campaign config (default: casual-professional)

## Output

- **personalized_message** (string)
  - Description: WhatsApp-ready message referencing specific pain points
  - Destination: Supabase `messages` table

- **queue_entry** (object)
  - Description: Scheduled dispatch entry
  - Destination: Supabase `message_queue` table

## Action Items

### Step 1: Load Lead Context
Fetch lead profile + context from Supabase. Identify strongest pain point.

### Step 2: Apply Value Equation
Frame message using Hormozi's Value Equation: Dream Outcome × Perceived Likelihood / Time Delay × Effort.

### Step 3: Craft Message (Halbert Style)
Write direct-response first-touch message:
- Open with specific reference to their business
- Identify pain point from context
- Hint at solution without selling
- Soft CTA (question, not pitch)

### Step 4: Quality Gate MC_001
Score personalization 1-10. Must be >= 7. Check:
- References specific company detail
- Mentions identified pain point
- Length 3-5 short paragraphs
- Natural tone (not template-like)

### Step 5: Queue for Dispatch
Save message to `messages` table. Create `message_queue` entry with status = 'scheduled'.

## Acceptance Criteria

- [ ] **AC-1:** Personalization score >= 7/10 (MC_001)
- [ ] **AC-2:** Message references specific context from lead's website
- [ ] **AC-3:** Length between 3-5 paragraphs
- [ ] **AC-4:** Message queued for dispatch with scheduled status

## Veto Conditions

- **Personalization < 5/10** → REJECT — re-craft with more context
- **No pain point referenced** → REJECT — generic messages forbidden
- **Message > 8 paragraphs** → REJECT — too long for WhatsApp
- **Lead without context** → ALLOW with basic personalization (company name + industry only)

## Handoff

| Attribute | Value |
|-----------|-------|
| **Next Task** | `schedule-dispatch` |
| **Trigger** | Message queued in message_queue |
| **Executor** | scheduler |

---

_Task Version: 1.0.0_
_Pattern: HO-TP-001 (Task Anatomy Standard)_
