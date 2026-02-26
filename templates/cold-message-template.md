# Cold Message Template

**Purpose:** Template base para mensagens personalizadas de WhatsApp (first-touch).
**Owner:** message-crafter
**Frameworks:** Value Equation (Hormozi) + Direct Response (Halbert)
**Quality Gate:** `checklists/message-quality-checklist.md`

---

## Template Structure

### Anatomy of a Cold WhatsApp Message

```
[HOOK] — 1 linha que prende atenção (referência específica ao lead)
[CONTEXT] — 1-2 linhas mostrando que você conhece o negócio dele
[VALUE] — 1-2 linhas com a proposta de valor (dream outcome + baixo esforço)
[CTA] — 1 linha com call-to-action simples e direto
```

**Total: 150-300 caracteres (WhatsApp optimal)**

---

## Variações por Contexto

### Variação A: Pain Point Identificado

```
Oi {nome_empresa}! Vi que vocês {serviço_que_oferecem} em {localização}.
{pain_point_específico} é um desafio comum nesse mercado.
Ajudamos {tipo_empresa_similar} a {resultado_específico} em {timeframe}.
Posso te mostrar como funciona em 5 min?
```

**Quando usar:** Context analyst identificou pain point claro (confidence >= 7/10)

### Variação B: Oportunidade Identificada

```
Oi {nome_empresa}! Vi o trabalho de vocês em {área_específica} — {elogio_genuíno}.
Tive uma ideia de como {oportunidade_específica} pode {resultado}.
{prova_social_rápida}.
Faz sentido conversar 5 min sobre isso?
```

**Quando usar:** Sem pain point claro, mas website mostra oportunidade de melhoria

### Variação C: Referência Local

```
{nome_empresa}, tudo bem? Vi vocês aqui em {bairro/região}.
Trabalho com {tipo_empresa} da região e {resultado_que_entrega}.
{diferencial_rápido}.
Posso mandar um exemplo do que fizemos pra {empresa_similar_região}?
```

**Quando usar:** Localização é diferencial forte, mercado regional

### Variação D: Sem Website (Dados Mínimos)

```
Oi {nome_empresa}! Vi vocês no Google Maps — {rating} estrelas, parabéns!
Trabalho ajudando {tipo_empresa} em {localização} a {resultado}.
Posso te mostrar como funciona?
```

**Quando usar:** Lead sem website, apenas dados do Google Maps disponíveis

---

## Placeholders

| Placeholder | Source | Required |
|-------------|--------|----------|
| `{nome_empresa}` | leads.company_name | YES |
| `{localização}` | leads.address (cidade/bairro) | YES |
| `{serviço_que_oferecem}` | lead_context.services_offered | NO |
| `{pain_point_específico}` | lead_context.pain_points[0] | NO |
| `{tipo_empresa_similar}` | ICP definition | YES |
| `{resultado_específico}` | Campaign value proposition | YES |
| `{timeframe}` | Realistic delivery time | YES |
| `{elogio_genuíno}` | Context extraction insight | NO |
| `{prova_social_rápida}` | Campaign social proof | NO |
| `{rating}` | leads.google_maps_rating | NO |

---

## Rules (Inline — Read Before Using)

### MUST DO
1. Replace ALL placeholders — zero `{placeholders}` in final message
2. Score personalization BEFORE queuing (>= 7/10)
3. Keep 150-300 characters
4. Use Portuguese BR natural (conversacional, não corporativo)
5. Single CTA — uma pergunta, uma ação

### MUST NOT
1. Include links in first message
2. Use ALL CAPS
3. Use more than 2-3 emojis
4. Make false claims or urgency
5. Send without context data (except Variação D)
6. Copy template verbatim — PERSONALIZE every message

### VETO if:
- Message reads like template (generic = spam)
- No reference to lead's specific business
- CTA is "vamos agendar uma reunião" (too formal for WhatsApp)
- Message > 300 chars
- Message < 100 chars (too short = suspicious)

---

## Selection Matrix

| Context Available | Pain Point | Website | Use Variação |
|-------------------|-----------|---------|-------------|
| Full context | YES | YES | **A** (Pain Point) |
| Partial context | NO | YES | **B** (Oportunidade) |
| Location strong | Any | Any | **C** (Referência Local) |
| Minimal data | NO | NO | **D** (Dados Mínimos) |

---

## Quality Gate

Before queuing, validate against `checklists/message-quality-checklist.md`:

1. [ ] Personalization >= 7/10
2. [ ] Length 150-300 chars
3. [ ] No links
4. [ ] Pain point or specific reference
5. [ ] Single CTA

---

**Template Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
