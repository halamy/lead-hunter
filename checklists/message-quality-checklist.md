# Message Quality Checklist

**Purpose:** Validate personalized messages before they enter the dispatch queue.
**Pattern:** HO-QG-001 (Quality Gate Standard)
**Mode:** BLOCKING — messages that fail critical checks are REJECTED.
**Owner:** message-crafter
**When:** Phase 4 of WF-Lead-Capture (after context extraction)

---

## 1. Personalization Score (Minimum 7/10)

### Scoring Criteria

| Criterion | Points | How to Score |
|-----------|--------|-------------|
| Uses company name correctly | 0-1 | Name present and spelled right |
| References specific service they offer | 0-1 | From context extraction |
| Mentions a pain point relevant to them | 0-2 | Specific, not generic |
| Tailored value proposition | 0-2 | Connects your offer to their need |
| Natural tone (not template-ish) | 0-2 | Reads like human wrote it |
| Local reference or specificity | 0-1 | Neighborhood, region, market reference |
| Call-to-action relevant to their context | 0-1 | Not generic "let's talk" |

**Total: 10 points**

### Validation

- [ ] Personalization score >= 7/10
- [ ] Score calculated and logged per message
- [ ] Low-scoring messages flagged for re-craft

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Score < 5/10 | REJECT — re-craft with better context |
| Score 5-6/10 | WARN — review before queuing |
| Score >= 7/10 | PASS — queue for dispatch |

---

## 2. Value Equation Check (Hormozi Framework)

- [ ] **Dream Outcome** mentioned — what they get
- [ ] **Perceived Likelihood** increased — proof or evidence
- [ ] **Time Delay** reduced — speed of result
- [ ] **Effort & Sacrifice** minimized — how easy it is

### Veto Conditions

| Condition | Action |
|-----------|--------|
| No dream outcome | REJECT — message has no hook |
| Generic promise ("vamos crescer juntos") | REJECT — zero specificity |

---

## 3. Direct Response Principles (Halbert Framework)

- [ ] **Opens with hook** — first line grabs attention
- [ ] **Specific, not vague** — numbers, names, details
- [ ] **Single CTA** — one clear next step
- [ ] **No corporate speak** — conversational WhatsApp tone
- [ ] **Urgency without desperation** — natural, not pushy

---

## 4. WhatsApp Format Compliance

- [ ] **Length: 150-300 characters** (optimal for WhatsApp)
- [ ] **No links in first message** (triggers spam filters)
- [ ] **No ALL CAPS** (looks like spam)
- [ ] **No excessive emojis** (max 2-3)
- [ ] **No attachments** in first touch
- [ ] **Portuguese BR natural** — not translated English

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Length > 300 chars | REJECT — too long for WhatsApp cold message |
| Contains links | REJECT — first message = no links |
| ALL CAPS detected | REJECT — reformulate |

---

## 5. Anti-Spam Compliance

- [ ] **No misleading subject** — honest about who you are
- [ ] **No false urgency** ("última vaga", "só hoje")
- [ ] **Opt-out friendly** — doesn't pressure response
- [ ] **LGPD compliant** — no personal data misuse
- [ ] **No competitor bashing** — professional tone

---

## 6. Context Integration Check

- [ ] **Context from website used** — not just company name
- [ ] **Pain point from context_analyst** referenced
- [ ] **Service alignment** visible (your offer matches their need)
- [ ] **No context = no personalization = REJECT**

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Message crafted without context data | REJECT — wait for context extraction |
| Pain point reference is generic | WARN — improve specificity |

---

## Validation Summary

### Quick Check (5 Critical Items)

1. [ ] Personalization >= 7/10
2. [ ] Length 150-300 chars
3. [ ] No links in first message
4. [ ] Specific pain point referenced
5. [ ] Single clear CTA

### Decision Matrix

| Score | Status | Action |
|-------|--------|--------|
| 5/5 critical passed | QUEUE | Send to message_queue |
| 4/5 critical passed | REVIEW | Human review before queue |
| < 4/5 critical passed | REJECT | Re-craft message |

---

**Checklist Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Phase:** WF-Lead-Capture Phase 4
