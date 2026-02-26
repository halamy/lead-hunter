# ICP Definition Template

**Purpose:** Template estruturado para definir Ideal Customer Profile antes da captura.
**Owner:** lead-qualifier
**Framework:** Sales Development Playbook (Trish Bertuzzi) + Predictable Revenue (Aaron Ross)
**Quality Gate:** `checklists/lead-qualification-checklist.md`

---

## ICP Card

```yaml
icp:
  campaign_name: "{nome_da_campanha}"
  created_at: "{YYYY-MM-DD}"
  created_by: "{quem_definiu}"

  # ═══════════════════════════════════════
  # TARGET DEFINITION
  # ═══════════════════════════════════════

  target:
    industry: "{vertical_específica}"
    # Instrução: Seja específico. "Marketing digital" > "Marketing" > "Serviços"
    # VETO se: "qualquer" ou "diversos"

    sub_industry: "{sub_nicho}"
    # Instrução: Opcional mas recomendado. "SEO local" > "Marketing digital"

    company_size:
      employees_min: {N}
      employees_max: {N}
      # Instrução: Range realista. 1-10 = micro, 11-50 = pequena, 51-200 = média

    location:
      city: "{cidade}"
      state: "{UF}"
      neighborhood: "{bairro}"  # Opcional — Google Maps aceita
      # VETO se: vazio. Google Maps PRECISA de localização.

    revenue_signals:
      - "{sinal_1}"
      - "{sinal_2}"
      # Instrução: Google rating >= 4.0? Múltiplas unidades? Website profissional?

  # ═══════════════════════════════════════
  # SCORING FRAMEWORK (30 Points)
  # ═══════════════════════════════════════

  scoring:
    threshold: 21  # Mínimo para qualificar (70%). Ajustável.

    dimensions:
      - name: "Industry Fit"
        weight: 5
        criteria:
          score_5: "{critério para 5 pontos}"
          score_3: "{critério para 3 pontos}"
          score_1: "{critério para 1 ponto}"
          score_0: "{critério para 0 pontos}"

      - name: "Company Size"
        weight: 5
        criteria:
          score_5: "Dentro do range ideal"
          score_3: "Próximo do range"
          score_1: "Fora do range mas viável"
          score_0: "Completamente fora"

      - name: "Location Match"
        weight: 5
        criteria:
          score_5: "Mesma cidade/região alvo"
          score_3: "Região metropolitana"
          score_1: "Mesmo estado"
          score_0: "Fora do estado"

      - name: "Online Presence"
        weight: 5
        criteria:
          score_5: "Website profissional + Google 4.5+ + ativo"
          score_3: "Website básico + Google 3.5+"
          score_1: "Só Google Maps, sem site"
          score_0: "Sem presença online"

      - name: "Service Alignment"
        weight: 5
        criteria:
          score_5: "{critério — serviço deles se beneficia do seu}"
          score_3: "{critério — benefício parcial}"
          score_1: "{critério — benefício indireto}"
          score_0: "{critério — sem conexão}"

      - name: "Growth Indicators"
        weight: 5
        criteria:
          score_5: "Contratando + expandindo + reviews recentes"
          score_3: "Ativo mas estável"
          score_1: "Poucas atividades recentes"
          score_0: "Parece inativo"

  # ═══════════════════════════════════════
  # DISQUALIFICATION RULES (Hard Blocks)
  # ═══════════════════════════════════════

  disqualification:
    auto_skip:
      - condition: "Sem telefone"
        reason: "GMH_001 — WhatsApp outreach requires phone"
      - condition: "Competidor direto"
        keywords: ["{keyword_1}", "{keyword_2}"]
        reason: "Competitor — não prospectar"
      - condition: "Já no banco de dados"
        check: "dedup by phone (GMH_003)"
        reason: "Duplicata"
      - condition: "Status closed-lost"
        check: "leads.status = 'closed-lost'"
        reason: "HARD BLOCK — respeitar opt-out"

    manual_review:
      - condition: "ICP score 15-20"
        action: "Flag para revisão humana"
      - condition: "Dados incompletos"
        action: "Tentar enriquecer antes de descartar"

  # ═══════════════════════════════════════
  # SEARCH QUERY (Google Maps)
  # ═══════════════════════════════════════

  search_query:
    primary: '"{industry}" "{city}, {state}"'
    alternatives:
      - '"{sub_industry}" "{city}"'
      - '"{industry}" "{neighborhood}, {city}"'
    # Instrução: Teste a query no Google Maps antes de rodar.
    # VETO se: 0 resultados ou > 10.000 resultados

  # ═══════════════════════════════════════
  # VALUE PROPOSITION (For Message Crafting)
  # ═══════════════════════════════════════

  value_proposition:
    product_service: "{o_que_você_vende}"
    dream_outcome: "{resultado_que_o_lead_quer}"
    pain_points_to_target:
      - "{dor_1}"
      - "{dor_2}"
    differentiator: "{por_que_você_e_não_a_concorrência}"
    social_proof: "{prova_de_resultado}"
```

---

## How to Fill (Step by Step)

### Step 1: Target Definition
Preencha `target` com dados específicos. Se não sabe o sub_industry, deixe vazio mas preencha industry.

### Step 2: Scoring Criteria
Para cada dimensão, defina o que significa score 5, 3, 1 e 0. Isso garante scoring consistente.

### Step 3: Disqualification
Liste os hard blocks. Mínimo: sem telefone + competidor + duplicata + closed-lost.

### Step 4: Search Query
Monte a query e TESTE no Google Maps. Se não retorna resultados, ajuste.

### Step 5: Value Proposition
O message-crafter precisa disso para personalizar. Sem value prop = mensagens genéricas.

---

## Validation

Antes de aprovar, rodar `checklists/lead-qualification-checklist.md`:

- [ ] >= 3 dimensions defined
- [ ] Threshold >= 21/30
- [ ] Search query tested
- [ ] Disqualification rules cover basics
- [ ] Value proposition clear

---

**Template Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
