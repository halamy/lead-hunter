# Handoff Package Template

**Purpose:** Template padronizado para handoff de leads qualificados para o sales-closer squad.
**Owner:** hunter-chief
**Destination:** sales-closer:closer-chief
**Quality Gate:** `checklists/handoff-readiness-checklist.md`

---

## Handoff Package Structure

```yaml
handoff:
  id: "HO-{lead_id}-{timestamp}"
  created_at: "{YYYY-MM-DD HH:MM:SS}"
  source_squad: "lead-hunter"
  destination_squad: "sales-closer"
  destination_agent: "closer-chief"

  # ═══════════════════════════════════════
  # LEAD PROFILE
  # ═══════════════════════════════════════

  lead_profile:
    lead_id: "{uuid}"                    # REQUIRED
    company_name: "{string}"             # REQUIRED
    phone: "{+55 XX XXXXX-XXXX}"         # REQUIRED
    website: "{url|null}"                # OPTIONAL
    address: "{string}"                  # REQUIRED
    google_maps_rating: "{number|null}"  # OPTIONAL
    icp_score: "{number}/30"             # REQUIRED
    captured_at: "{datetime}"            # REQUIRED
    source: "Google Maps"                # REQUIRED
    decision_maker: "{string|null}"      # ENRICHED — Google Maps não captura.
                                         # Identificado durante SPIN qualification
                                         # no sales-closer (conversation-manager).
                                         # Se disponível no website, context-analyst preenche.

  # ═══════════════════════════════════════
  # CONTEXT INTELLIGENCE
  # ═══════════════════════════════════════

  context_summary:
    pain_points:                         # REQUIRED (min 1)
      - pain: "{dor_identificada}"
        source: "{onde_foi_identificada}"
        confidence: "{1-10}"

    services_offered:                    # REQUIRED
      - "{serviço_1}"
      - "{serviço_2}"

    company_size: "{micro|pequena|média|grande}"  # OPTIONAL
    tech_stack:                          # OPTIONAL
      - "{tecnologia_1}"

    urgency_signals:                     # OPTIONAL
      - signal: "{sinal}"
        evidence: "{evidência}"

    budget_signals:                      # OPTIONAL
      - signal: "{sinal}"
        evidence: "{evidência}"

    confidence_score: "{1-10}"           # REQUIRED

  # ═══════════════════════════════════════
  # CONVERSATION HISTORY
  # ═══════════════════════════════════════

  conversation:
    outreach:
      message_text: "{texto_da_mensagem_enviada}"    # REQUIRED
      sent_at: "{YYYY-MM-DD HH:MM:SS BRT}"          # REQUIRED
      personalization_score: "{number}/10"            # REQUIRED
      template_variation: "{A|B|C|D}"                # OPTIONAL

    response:
      response_text: "{texto_da_resposta_do_lead}"   # REQUIRED
      received_at: "{YYYY-MM-DD HH:MM:SS BRT}"      # REQUIRED
      sentiment: "{positive|neutral|unclear}"         # REQUIRED
      time_to_response: "{duration}"                  # REQUIRED

  # ═══════════════════════════════════════
  # QUALIFICATION & RECOMMENDATION
  # ═══════════════════════════════════════

  qualification:
    icp_score: "{number}/30"             # REQUIRED
    personalization_score: "{number}/10"  # REQUIRED
    response_sentiment: "{string}"       # REQUIRED
    response_speed: "{fast|medium|slow}" # OPTIONAL
    # fast = < 1h, medium = 1-4h, slow = > 4h

    recommended_approach: |              # OPTIONAL
      {Sugestão para o closer baseada no contexto.
       Ex: "Lead demonstrou interesse em X. Focar na dor Y.
       Resposta rápida indica urgência — não demorar para seguir."}

    hot_buttons:                         # OPTIONAL
      - "{gatilho_emocional_1}"
      - "{gatilho_emocional_2}"

  # ═══════════════════════════════════════
  # METADATA
  # ═══════════════════════════════════════

  metadata:
    handoff_version: "1.0.0"
    pipeline_duration: "{tempo_total_no_pipeline}"
    phases_completed:
      qualify: true
      capture: true
      context: true
      craft: true
      dispatch: true
      response: true
    quality_gate_passed: true
    checklist_ref: "checklists/handoff-readiness-checklist.md"
```

---

## Required vs Optional Fields

| Field | Required | Why |
|-------|----------|-----|
| lead_id | YES | Unique identifier |
| company_name | YES | Closer needs to know who |
| phone | YES | Primary contact channel |
| icp_score | YES | Quality indicator |
| pain_points (>= 1) | YES | Closer ammunition |
| services_offered | YES | Context for conversation |
| outreach message_text | YES | What was said |
| response_text | YES | What they replied |
| sentiment | YES | Classification |
| confidence_score | YES | Reliability indicator |
| personalization_score | YES | Quality indicator |
| time_to_response | YES | Urgency indicator |
| decision_maker | ENRICHED | Identified during SPIN in sales-closer. Pre-filled by context-analyst if found on website. |

---

## Completeness Scoring

| Required Fields | Score | Status |
|----------------|-------|--------|
| 12/12 | 100% | PASS — hand off now |
| 10-11/12 | 83-92% | CONDITIONAL — hand off with gaps noted |
| < 10/12 | < 83% | BLOCK — complete package first |

---

## Instructions for sales-closer

When receiving this package:

1. **Read pain_points first** — this is your opening angle
2. **Read response_text** — understand their mindset
3. **Check time_to_response** — fast = high interest, act immediately
4. **Use recommended_approach** if available
5. **Reference outreach message** — continuity matters, don't repeat yourself
6. **Check hot_buttons** — emotional triggers for closing

---

## Validation

Before sending, run `checklists/handoff-readiness-checklist.md`:

1. [ ] Sentiment = positive
2. [ ] Lead profile has company_name + phone
3. [ ] Context has >= 1 pain point
4. [ ] Conversation has outreach + response
5. [ ] ICP score >= 21/30

**All 5 PASS = hand off. Zero exceptions.**

---

**Template Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter → sales-closer
