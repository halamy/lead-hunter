# Lead Qualification Checklist

**Purpose:** Validate ICP definition and qualification criteria before any lead capture begins.
**Pattern:** HO-QG-001 (Quality Gate Standard)
**Mode:** BLOCKING — capture cannot start if critical items fail.
**Owner:** lead-qualifier
**When:** Phase 1 of WF-Lead-Capture

---

## 1. ICP Dimensions (Minimum 3 Required)

- [ ] **Industry defined** — Specific vertical, not "anything"
- [ ] **Company size defined** — Employee count or revenue range
- [ ] **Location defined** — City + State minimum (Google Maps needs this)
- [ ] **Online presence criteria** — Website required? Google rating minimum?
- [ ] **Service alignment** — What they sell aligns with what you offer
- [ ] **Growth indicators** — Hiring? Multiple locations? Recent reviews?

### Veto Conditions

| Condition | Action |
|-----------|--------|
| < 3 dimensions defined | BLOCK — refine ICP before capture |
| Industry = "qualquer" | BLOCK — too broad, zero targeting |
| Location not defined | BLOCK — Google Maps requires geographic query |

---

## 2. Scoring Framework (30-Point System)

- [ ] **6 dimensions scored** (5 points each = 30 total)
- [ ] **Weights assigned** per dimension
- [ ] **Threshold defined** (default >= 21/30 = 70%)
- [ ] **Disqualification rules** documented (hard blocks)

### Scoring Dimensions

| Dimension | Points | Criteria |
|-----------|--------|----------|
| Industry fit | 0-5 | How close to target vertical |
| Company size | 0-5 | Within ideal range |
| Location match | 0-5 | Geographic proximity to target |
| Online presence | 0-5 | Website quality, reviews, activity |
| Service alignment | 0-5 | Overlap with your offering |
| Growth indicators | 0-5 | Signals of expansion/investment |

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Threshold < 15/30 | WARN — too permissive, recommend >= 21 |
| No scoring weights | BLOCK — arbitrary scoring = random results |
| No disqualification rules | BLOCK — every bad lead enters pipeline |

---

## 3. Search Query Validation

- [ ] **Query formulated** from ICP dimensions
- [ ] **Format valid:** `"{industry}" "{city}, {state}"`
- [ ] **Not too broad** — "empresa São Paulo" = millions of results
- [ ] **Not too narrow** — "agência SEO premium Pinheiros" = 3 results
- [ ] **Test query returns results** (manual or API check)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| Query too broad (1-word industry) | BLOCK — refine to specific vertical |
| Query returns 0 results | BLOCK — adjust query before proceeding |
| No location in query | BLOCK — Google Maps requires geography |

---

## 4. Disqualification Rules

- [ ] **No phone = auto-skip** (GMH_001 — non-negotiable)
- [ ] **Competitor detection** — keywords/names that auto-disqualify
- [ ] **Already in database** — dedup by phone number (GMH_003)
- [ ] **Closed-lost leads** — HARD BLOCK reentry

---

## 5. Campaign Context

- [ ] **Product/service being sold** is clear
- [ ] **Value proposition** defined (what problem you solve)
- [ ] **Target pain points** identified (minimum 2)
- [ ] **Differentiator** documented (why you vs competition)

### Veto Conditions

| Condition | Action |
|-----------|--------|
| No value proposition | BLOCK — messages will be generic spam |
| Pain points < 2 | WARN — personalization will be weak |

---

## Validation Summary

### Scoring

| Section | Items | Weight |
|---------|-------|--------|
| ICP Dimensions | 6 | 30% |
| Scoring Framework | 4 | 25% |
| Search Query | 5 | 20% |
| Disqualification Rules | 4 | 15% |
| Campaign Context | 4 | 10% |

### Decision Matrix

| Score | Status | Action |
|-------|--------|--------|
| 100% blocking passed | GO | Proceed to Phase 2 (capture) |
| 1+ blocking failed | NO-GO | Fix before capture |

---

**Checklist Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Phase:** WF-Lead-Capture Phase 1
