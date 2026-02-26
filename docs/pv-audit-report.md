# Auditoria Completa — Lead Hunter Squad
# Pedro Valério | Process Absolutist
# Data: 2026-02-26

---

## RESUMO EXECUTIVO

**Squad:** Lead Hunter v1.0.0
**Artefatos auditados:** 7 agents, 7 tasks, 1 workflow (6 fases), 5 checklists, 1 schema + 1 migration
**Veredicto:** APROVADO COM RESSALVAS — Arquitetura 85%, Implementação 35%

---

## PARTE A — AUDITORIA DOS 7 AGENTS

### 1. hunter-chief (Orchestrator) — ✅ APROVADO

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Orchestrator, coordena tudo |
| Veto conditions | ✅ | 3 vetos documentados (ICP, closed-lost, horário) |
| Handoff definido | ✅ | 8 handoffs mapeados (6 internos + 1 sales-closer + 1 system) |
| Smoke tests | ✅ | 3 testes com expected signals e red flags |
| Anti-patterns | ✅ | 7 "never_do" + 3 "always_do" |
| Heurísticas | ✅ | 5 heurísticas (LH_HE_001 a LH_HE_005) |
| Auto-triggers | ✅ | 2 triggers com 5 guardrails cada (LH_AT_001, LH_AT_005) |

**Desvios:** Nenhum crítico.
**Observação:** Referencia `sales-closer:closer-chief` no handoff — ✅ CONFIRMADO que existe.

---

### 2. lead-qualifier (Tier 0) — ✅ APROVADO

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 0 — primeiro gate |
| Veto conditions | ✅ | 5 vetos (ICP < 21, pain points < 2, geography, decision maker, timeout 24h) |
| Scoring framework | ✅ | 30 pontos, 6 dimensões × 5 |
| Timeout veto | ✅ | 24h auto-cancel — EXCELENTE |
| Handoff definido | ✅ | → google-maps-hunter |
| Smoke tests | ✅ | 3 testes |

**Desvios:** Nenhum.
**Ponto forte:** Timeout de 24h para ICP incompleto — processo que se auto-limpa.

---

### 3. google-maps-hunter (Tier 1) — ⚠️ APROVADO COM RESSALVA

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 1 — captura |
| Veto conditions | ✅ | 3 vetos (sem phone, target atingido, >20% inválidos) |
| Heurísticas | ✅ | GMH_001 (phone), GMH_002 (website priority), GMH_003 (dedup) |
| Handoff definido | ✅ | 3 handoffs (context-analyst, database-manager, hunter-chief) |
| Smoke tests | ✅ | 3 testes |

**❌ DESVIO CRÍTICO:** Referencia `google-maps-scraper.py` em dependencies.scripts — **ARQUIVO NÃO EXISTE**.
- **Impacto:** Phase 2 inteira não executa.
- **Ação:** Criar task de implementação (ver Parte B, Gap #1).

---

### 4. message-crafter (Tier 1) — ✅ APROVADO

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 1 — mensagens |
| Veto conditions | ✅ | 4 vetos (personalization < 5, no pain point, > 8 parágrafos, sem contexto) |
| Frameworks | ✅ | Value Equation (Hormozi) + Direct Response (Halbert) |
| Quality gate MC_001 | ✅ | Score >= 7/10 obrigatório |
| Handoff definido | ✅ | → scheduler |
| Smoke tests | ✅ | 3 testes |

**Desvios:** Nenhum crítico.
**Observação:** Referencia `cold-message-template.md` e `value-proposition-library.yaml` — verificar se existem.

---

### 5. context-analyst (Tier 2) — ⚠️ APROVADO COM RESSALVA

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 2 — extração |
| Veto conditions | ⚠️ | 3 vetos documentados mas enforcement é via agent, não DB |
| Extraction strategy | ✅ | 4 páginas: homepage, services, about, contact |
| Handoff definido | ✅ | → message-crafter |
| Smoke tests | ✅ | 3 testes |

**❌ DESVIO CRÍTICO:** Referencia `website-scraper.py` e `context-parser.py` — **ARQUIVOS NÃO EXISTEM**.
- **Impacto:** Phase 3 inteira não executa.
- **Ação:** Criar task de implementação (ver Parte B, Gap #2).

---

### 6. database-manager (Tier 2) — ✅ APROVADO

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 2 — Supabase |
| State machine | ✅ | 10 estados com transições válidas documentadas |
| Enforcement | ✅ | Trigger `enforce_lead_status_transition()` no banco |
| Veto conditions | ✅ | 3 vetos (context > 2h, retry >= 3, duplicata) |
| Auto-triggers | ✅ | LH_AT_002 com 5 guardrails |
| Handoff definido | ✅ | → hunter-chief (2 cenários) |
| Smoke tests | ✅ | 3 testes |

**Desvios:** Nenhum.
**Ponto forte:** State machine mais detalhada que a do CLAUDE.md (inclui delivered, read, failed, context_failed).

---

### 7. scheduler (Tier 2) — ⚠️ APROVADO COM RESSALVA

| Critério | Status | Nota |
|----------|--------|------|
| Owner definido | ✅ | Tier 2 — dispatch |
| Veto conditions | ✅ | 3 vetos hard (time window, hourly, daily) |
| Anti-detection | ✅ | Random 30-180s, distribute across window |
| Rate limiting | ✅ | 30/hr, 200/day |
| Handoff definido | ✅ | → hunter-chief + database-manager |
| Smoke tests | ✅ | 3 testes |

**❌ DESVIO CRÍTICO:** Referencia `queue-processor.py` e `whatsapp-api-client.py` — **ARQUIVOS NÃO EXISTEM**.
- **Impacto:** Phase 5 inteira não executa.
- **Ação:** Criar task de implementação (ver Parte B, Gap #3).

---

## PARTE A.2 — AUDITORIA DO WORKFLOW

### WF-Lead-Capture — ✅ APROVADO (Design)

| Critério | Status | Nota |
|----------|--------|------|
| 6 fases definidas | ✅ | PHASE-1 a PHASE-6 |
| Checkpoints por fase | ✅ | 6 checkpoints, todos com veto condition |
| Human review | ✅ | Phase 1 (ICP) e Phase 4 (mensagens) |
| Unidirecional | ✅ | `return_to_previous_phase: false` explícito |
| Error handling | ✅ | Específico por tipo (Google Maps, WhatsApp, scrape) |
| Agent assignments | ✅ | Primary + secondary por fase |
| Governance gate | ✅ | Referencia ai-first-governance.md |

**Desvio identificado:**
- `error_handling.on_checkpoint_failure.return_to_previous_phase: false` — ✅ Correto, fluxo unidirecional.
- Mas `halt_workflow: false` em `on_phase_failure` — ⚠️ Se Phase 2 falha (0 leads), pipeline continua vazia. **Deveria ser `halt_workflow: true` quando 0 leads.**

---

## PARTE A.3 — AUDITORIA DAS 7 TASKS

| Task | Owner | Veto Conditions | Handoff | AC | Status |
|------|-------|----------------|---------|-----|--------|
| qualify-lead | lead-qualifier | ✅ 3 vetos | ✅ → capture-leads | 4 ACs | ✅ |
| capture-leads | google-maps-hunter | ✅ 3 vetos | ✅ → extract-context | 5 ACs | ✅ |
| extract-context | context-analyst | ✅ 3 vetos | ✅ → craft-message | 4 ACs | ✅ |
| craft-message | message-crafter | ✅ 4 vetos | ✅ → schedule-dispatch | 4 ACs | ✅ |
| schedule-dispatch | scheduler | ✅ 4 vetos | ✅ → process-responses | 5 ACs | ✅ |
| process-responses | hunter-chief | ✅ 3 vetos | ✅ → sales-closer | 4 ACs | ✅ |
| pipeline-report | hunter-chief | ✅ 2 vetos | — (terminal) | 3 ACs | ✅ |

**Todas as tasks seguem padrão HO-TP-001. Zero desvios de estrutura.**

---

## PARTE A.4 — AUDITORIA DOS 5 CHECKLISTS

| Checklist | Mode | Owner | Veto Conditions | Quick Check | Status |
|-----------|------|-------|----------------|-------------|--------|
| lead-qualification | BLOCKING | lead-qualifier | ✅ 8 vetos | 5 itens | ✅ |
| message-quality | BLOCKING | message-crafter | ✅ 5 vetos | 5 itens | ✅ |
| dispatch-safety | BLOCKING | scheduler | ✅ 9 vetos + 5 guardrails | 5 itens | ✅ |
| pipeline-health | ADVISORY | hunter-chief | ✅ 6 alertas | — | ✅ |
| handoff-readiness | BLOCKING | hunter-chief | ✅ 6 vetos | 5 itens | ✅ |

**Ponto forte:** dispatch-safety-checklist tem os 5 guardrails obrigatórios (PV008).
**Ponto forte:** Todos os checklists BLOCKING têm quick validation de 5 itens críticos.

---

## PARTE A.5 — AUDITORIA DO SCHEMA + MIGRATION

### Schema Base (supabase-schema.sql)

| Tabela | Status | Enforcement |
|--------|--------|-------------|
| leads | ✅ | CHECK constraint em status |
| lead_context | ✅ | UNIQUE(lead_id), FK cascade |
| messages | ✅ | CHECK em status e personalization_score |
| lead_responses | ✅ | CHECK em sentiment |
| message_queue | ✅ | CHECK em status e priority |
| archived_leads | ✅ | CHECK em retry_status |
| retry_queue | ✅ | FK cascade, CHECK status |

**3 views úteis:** pipeline_overview, todays_activity, leads_ready_for_handoff.
**3 functions:** archive_non_responders, process_retry_queue, cleanup_failed_retries.

### Migration 001 (P0 Veto Enforcement)

| Fix | Enforcement | Status |
|-----|------------|--------|
| P0-1: State machine | Trigger enforce_lead_status_transition() | ✅ FÍSICO |
| P0-1: Message state | Trigger enforce_message_status_transition() | ✅ FÍSICO |
| P0-2: Handoff queue | Tabela handoff_queue + auto-trigger | ✅ FÍSICO |
| P0-2: Handoff rejections | Tabela handoff_rejections | ✅ FÍSICO |
| P0-3: Dedup phone | UNIQUE partial index (active only) | ✅ FÍSICO |
| P0-4: Rate limit | rate_limit_log + check_rate_limit() | ✅ FÍSICO |
| P0-4: Business hours | Trigger enforce_business_hours_on_queue() | ✅ FÍSICO |
| P0-6: ICP alignment | icp_score 1-30 + enforce_icp_threshold() | ✅ FÍSICO |
| Personalization min | Trigger enforce_personalization_minimum() | ✅ FÍSICO |

**EXCELENTE.** 9 veto conditions transformadas em bloqueios físicos no banco.
Processo que impossibilita caminhos errados no nível de dados.

---

## PARTE A.6 — AUDITORIA DO HANDOFF (lead-hunter → sales-closer)

### Lado Lead Hunter

| Item | Status | Nota |
|------|--------|------|
| Trigger definido | ✅ | `lead_responded == true AND sentiment == positive` |
| Package definido | ✅ | 4 required (profile, context, conversation, score) + 3 optional |
| Checklist | ✅ | handoff-readiness-checklist com 5 critical checks |
| DB enforcement | ✅ | Trigger `auto_create_handoff_on_response()` cria entry automática |
| Return path | ✅ | Tabela `handoff_rejections` para feedback do sales-closer |
| TTL | ✅ | 4 horas para pickup |

### Lado Sales Closer

| Item | Status | Nota |
|------|--------|------|
| Entry gate | ✅ | conversation-gatekeeper com 6 critérios obrigatórios |
| Re-qualificação | ✅ | 25 pontos, 5 dimensões |
| Routing | ✅ | PASS (≥12) / WARM_UP (8-11) / REJECT (<8) |
| Rejection path | ✅ | Devolve para lead-hunter com motivo |

### Gap Identificado

**❌ GAP: Protocolo de comunicação entre squads.**
- `handoff_queue` no Supabase do lead-hunter ✅
- Sales-closer sabe que precisa ler de `handoff_queue` ✅
- **MAS:** Não há trigger/webhook/cron que NOTIFIQUE sales-closer de novo entry.
- **Impacto:** Sales-closer precisa fazer polling manual na `handoff_queue`.
- **Fix:** Ver Parte B, Gap #4 — Criar auto-trigger LH_AT_008 com notificação.

---

## PARTE B — TASKS PARA GAPS CRÍTICOS

### Gap #1: Google Maps Integration

```yaml
task:
  name: implement-google-maps-scraper
  id: implement-gmaps
  status: pending
  responsible_executor: "@dev"
  execution_type: Hybrid
  estimated_time: 8h
  priority: P0

  description: |
    Implementar integração com Google Maps para captura de leads.
    Opções: Google Places API (oficial), Apify Actor (scraping), ou SerpAPI.
    DEVE extrair: company_name, phone, website, address, rating, category.

  input:
    - ICP search query (ex: "agência marketing digital São Paulo")
    - Target count
    - ICP criteria for inline filtering

  output:
    - Script/integração funcional que retorna leads formatados
    - Insert direto no Supabase (leads table)
    - Capture report com métricas

  veto_conditions:
    - SE não extrai phone → não serve (GMH_001 é inviolável)
    - SE rate limit da API não configurado → VETO (sem guardrail)
    - SE sem dedup check antes do insert → VETO (GMH_003)
    - SE output não tem os 6 campos obrigatórios → VETO

  implementation_options:
    option_a:
      name: "Google Places API (Oficial)"
      pros: "Estável, legal, structured data"
      cons: "Custo por request, phone nem sempre disponível"
      cost: "$17/1000 requests (Nearby Search)"

    option_b:
      name: "Apify Actor (Google Maps Scraper)"
      pros: "Extrai mais dados, phone mais frequente, custo baixo"
      cons: "Scraping (ToS risk), pode quebrar"
      cost: "~$5/1000 results"
      actor: "compass/crawler-google-places"

    option_c:
      name: "SerpAPI (Google Maps)"
      pros: "API estável, structured response"
      cons: "Custo médio, rate limits"
      cost: "$50/mo (5000 searches)"

  recommendation: "Option B (Apify) — melhor custo-benefício, mais dados, phone frequente"

  action_items:
    - "[ ] Avaliar e selecionar provider (A/B/C)"
    - "[ ] Implementar extração com os 6 campos"
    - "[ ] Implementar dedup check (GMH_003)"
    - "[ ] Implementar insert no Supabase"
    - "[ ] Testar com query real e validar taxa de phone"
    - "[ ] Documentar limites e custos"
```

### Gap #2: Website Scraper (Context Extraction)

```yaml
task:
  name: implement-website-scraper
  id: implement-scraper
  status: pending
  responsible_executor: "@dev"
  execution_type: Hybrid
  estimated_time: 6h
  priority: P0

  description: |
    Implementar extração de contexto de websites de leads.
    DEVE escanear: homepage, about, services, contact.
    DEVE identificar: services, pain points, company size, tech stack.
    Output vai para lead_context table no Supabase.

  input:
    - Lead com website URL (do Supabase)
    - Pain point patterns (reference list)

  output:
    - Context record no Supabase (lead_context table)
    - Context score (1-10)
    - Pain points array

  veto_conditions:
    - SE não tenta retry em falha → VETO (max 3, LH_AT_002)
    - SE inventa dados não presentes no site → VETO ABSOLUTO
    - SE não atualiza status do lead (new → context_pending → ready) → VETO
    - SE context_score > 5 quando só tem nome → VETO

  implementation_options:
    option_a:
      name: "Playwright MCP (já disponível)"
      pros: "JS rendering, já instalado, Claude pode analisar"
      cons: "Lento por lead, memory-intensive"

    option_b:
      name: "Apify Web Scraper Actor"
      pros: "Escalável, paralelo, cost-effective"
      cons: "Precisa configurar Actor"

    option_c:
      name: "Claude + WebFetch (nativo)"
      pros: "Zero infra adicional, Claude analisa diretamente"
      cons: "Sem JS rendering, rate limits"

  recommendation: "Option C (WebFetch) para MVP → Option A (Playwright) para scale"

  action_items:
    - "[ ] Implementar fetch de 4 páginas (homepage, about, services, contact)"
    - "[ ] Implementar extração de pain points via LLM analysis"
    - "[ ] Implementar scoring (1-10)"
    - "[ ] Implementar retry logic (max 3, exponential backoff)"
    - "[ ] Implementar fallback para leads sem website"
    - "[ ] Insert em lead_context + update lead status"
```

### Gap #3: WhatsApp API Integration

```yaml
task:
  name: implement-whatsapp-dispatch
  id: implement-whatsapp
  status: pending
  responsible_executor: "@dev"
  execution_type: Hybrid
  estimated_time: 10h
  priority: P0

  description: |
    Implementar integração com WhatsApp API para dispatch de mensagens.
    DEVE respeitar: 9h-17h BRT, 30/hr, 200/day, delays 30-180s.
    DEVE integrar com Supabase: message_queue → WhatsApp → status update.

  input:
    - message_queue entries (Supabase)
    - WhatsApp Business API credentials

  output:
    - Mensagens enviadas via WhatsApp
    - Status updates no Supabase (leads + messages)
    - Rate limit logging (rate_limit_log table)
    - Dispatch report

  veto_conditions:
    - SE permite envio fora de 9h-17h → VETO ABSOLUTO
    - SE não checa rate_limit antes de cada envio → VETO
    - SE delay não é randomizado (30-180s) → VETO
    - SE não loga em rate_limit_log → VETO (sem audit trail)
    - SE não tem manual escape (*pause-dispatch) → VETO

  implementation_options:
    option_a:
      name: "WhatsApp Business API (Oficial via Meta)"
      pros: "Oficial, confiável, webhooks nativos"
      cons: "Aprovação demorada, custo por mensagem"
      cost: "~R$0.25/conversa iniciada"

    option_b:
      name: "Evolution API (Self-hosted)"
      pros: "Gratuito, controle total, sem aprovação"
      cons: "Risco de ban, manutenção própria"

    option_c:
      name: "Z-API (SaaS brasileiro)"
      pros: "Fácil setup, webhooks, dashboard"
      cons: "Custo mensal, dependência"
      cost: "~R$100-300/mês"

  recommendation: "Option B (Evolution API) para MVP → Option A (Meta oficial) para scale"

  guardrails:
    - "Loop prevention: processed flag por message_id (1x)"
    - "Idempotency: idempotency_key no Supabase"
    - "Audit trail: rate_limit_log + message status"
    - "Manual escape: *pause-dispatch command"
    - "Retry logic: 3x exponential backoff"

  action_items:
    - "[ ] Selecionar provider (A/B/C)"
    - "[ ] Implementar client de envio com error handling"
    - "[ ] Implementar time window check (9h-17h BRT)"
    - "[ ] Implementar rate limit check (check_rate_limit() do Supabase)"
    - "[ ] Implementar random delay (30-180s)"
    - "[ ] Implementar retry logic (max 3)"
    - "[ ] Implementar webhook para delivery confirmation"
    - "[ ] Implementar *pause-dispatch command"
    - "[ ] Integrar com rate_limit_log table"
    - "[ ] Testar com número de teste antes de produção"
```

### Gap #4: Inter-Squad Notification (Handoff Trigger)

```yaml
task:
  name: implement-handoff-notification
  id: implement-handoff-notify
  status: pending
  responsible_executor: "@dev"
  execution_type: Hybrid
  estimated_time: 3h
  priority: P1

  description: |
    Implementar notificação automática quando lead entra no handoff_queue.
    Atualmente o trigger auto_create_handoff_on_response() cria o entry,
    MAS ninguém notifica o sales-closer que tem lead novo.

  input:
    - handoff_queue entry (criada pelo trigger P0-2)

  output:
    - Notificação para sales-closer squad
    - Confirmação de recebimento

  veto_conditions:
    - SE notificação falha e ninguém sabe → VETO (lead esfria)
    - SE sem TTL check (4h) → VETO (lead pode expirar sem ação)
    - SE sem retry em falha de notificação → VETO

  implementation_options:
    option_a:
      name: "Supabase Realtime (subscription)"
      pros: "Nativo, zero infra adicional"
      cons: "Precisa client escutando"

    option_b:
      name: "Supabase Edge Function + Webhook"
      pros: "Push notification, confiável"
      cons: "Precisa configurar Edge Function"

    option_c:
      name: "Cron polling (15min)"
      pros: "Simples, funciona sempre"
      cons: "Latência de até 15min"

  recommendation: "Option B (Edge Function) para zero gap de tempo"

  action_items:
    - "[ ] Criar Edge Function que dispara em INSERT no handoff_queue"
    - "[ ] Implementar notificação para sales-closer"
    - "[ ] Implementar TTL check (4h → expire pending entries)"
    - "[ ] Implementar retry em falha (max 3)"
    - "[ ] Testar end-to-end: lead responde → handoff_queue → notificação"
```

### Gap #5: Sentiment Classification

```yaml
task:
  name: implement-sentiment-classification
  id: implement-sentiment
  status: pending
  responsible_executor: "@dev"
  execution_type: Hybrid
  estimated_time: 4h
  priority: P1

  description: |
    Implementar classificação automática de sentimento das respostas.
    Atualmente LH_HE_004 define as regras mas não há implementação.
    DEVE classificar: positive, negative, neutral, interested, not_interested.

  input:
    - response_text do lead (lead_responses table)

  output:
    - sentiment classificado
    - confidence score
    - routing decision (handoff / closed-lost / manual review)

  veto_conditions:
    - SE classifica negativo como positivo → VETO CRÍTICO (falso handoff)
    - SE sem fallback para classificação incerta → VETO (manual review queue)
    - SE não respeita SLA 30min para unclear → VETO

  implementation:
    approach: "LLM-based classification via Claude API"
    prompt_template: |
      Classifique a resposta do lead:
      Contexto: {outreach_message}
      Resposta: {response_text}
      Classes: positive, negative, neutral, interested, not_interested
      Retorne: { sentiment, confidence, reasoning }
    fallback: "SE confidence < 0.7 → manual review queue"

  action_items:
    - "[ ] Implementar classificação via Claude API"
    - "[ ] Implementar threshold de confiança (>= 0.7 auto, < 0.7 manual)"
    - "[ ] Implementar routing automático baseado em classificação"
    - "[ ] Implementar logging de todas classificações (audit trail)"
    - "[ ] Testar com exemplos reais (10+ responses variadas)"
```

---

## PARTE C — PROTOCOLO DE HANDOFF (lead-hunter → sales-closer)

### Estado Atual ✅

```
Lead responde positivamente
  → Trigger auto_create_handoff_on_response() [P0-2 no banco]
    → Cria entry em handoff_queue com:
       - lead_profile (JSONB)
       - context_summary (JSONB)
       - response_received (TEXT)
       - qualification_score (INTEGER)
    → Status: 'pending'
    → TTL: 4 horas
```

### Fluxo Completo Validado

```
LEAD HUNTER                          SALES CLOSER
───────────────────────────────────────────────────
1. Lead status → 'responded'
   ↓
2. Trigger auto_create_handoff_on_response()
   ↓
3. INSERT handoff_queue (status='pending')
   ↓
4. [GAP] Notificação para sales-closer ← IMPLEMENTAR (Gap #4)
   ↓
5. conversation-gatekeeper valida:
   - 6 critérios obrigatórios
   - Re-qualificação 25 pontos
   ↓
6. Routing:
   PASS (≥12) → Phase 1 (conversa)
   WARM_UP (8-11) → Phase 6 (follow-up)
   REJECT (<8) → handoff_rejections table
   ↓
7. Se REJECT:
   INSERT handoff_rejections
   (rejection_reason, missing_fields)
   ↓
8. [RETURN PATH] lead-hunter processa rejeição:
   - Enriquecer contexto
   - Re-qualificar
   - Re-submeter
```

### Veto Conditions do Handoff (Consolidadas)

| # | Veto | Enforcement | Lado |
|---|------|-------------|------|
| 1 | Package incompleto | handoff-readiness-checklist | Lead Hunter |
| 2 | Sentiment ≠ positive | LH_HE_004 heuristic | Lead Hunter |
| 3 | ICP score < 21/30 | enforce_icp_threshold() trigger | Banco |
| 4 | Missing phone | entry-gate-checklist | Sales Closer |
| 5 | Duplicate in active conversations | UNIQUE check | Sales Closer |
| 6 | Response > 7 dias | entry-gate-checklist | Sales Closer |
| 7 | Re-qual score < 8/25 | conversation-gatekeeper | Sales Closer |

### Package Contract (Validado Ambos os Lados)

```yaml
# Lead Hunter ENVIA (handoff_queue):
handoff_queue:
  lead_profile: JSONB        # company, phone, website, address, icp_score
  context_summary: JSONB      # pain_points, services, urgency_signals, confidence
  response_received: TEXT     # texto literal da resposta
  qualification_score: INT    # 1-30 (ICP framework)

# Sales Closer ESPERA (entry-gate-checklist):
required:
  - phone: "+55 format"       # ✅ Presente em lead_profile.phone
  - context: "exists"         # ✅ Presente em context_summary
  - response: "exists"        # ✅ Presente em response_received
  - icp_score: ">= 21"       # ✅ Presente em qualification_score
  - sentiment: "positive"     # ⚠️ NÃO explícito no handoff_queue
```

### ⚠️ Gap no Contract: Campo `sentiment`

**Problema:** Sales-closer espera `sentiment` no package, mas `handoff_queue` não tem coluna `sentiment`.
**Impacto:** Gatekeeper precisa inferir sentiment da presença no handoff_queue (se está lá, é positivo).
**Fix recomendado:** Adicionar coluna `sentiment TEXT` ao `handoff_queue`.

```sql
ALTER TABLE handoff_queue ADD COLUMN IF NOT EXISTS sentiment TEXT
  DEFAULT 'positive'
  CHECK (sentiment IN ('positive', 'interested', 'question'));
```

---

## RESUMO DE AÇÕES

### P0 — Bloqueiam Execução

| # | Gap | Artefato | Status |
|---|-----|---------|--------|
| 1 | Google Maps scraper | `scripts/google-maps-scraper.py` | ✅ IMPLEMENTADO (Google Places API) |
| 2 | Website scraper | `scripts/website-scraper.py` | ✅ IMPLEMENTADO (httpx + BS4 + Claude) |
| 3 | WhatsApp API dispatch | `scripts/whatsapp-api-client.py` | ✅ IMPLEMENTADO (Evolution API) |

### P1 — Degradam Operação

| # | Gap | Artefato | Status |
|---|-----|---------|--------|
| 4 | Notificação inter-squad | `data/migrations/002_p1_handoff_sentiment.sql` (P1-2) | ✅ IMPLEMENTADO (notification table + function) |
| 5 | Classificação de sentimento | `scripts/sentiment-classifier.py` | ✅ IMPLEMENTADO (Claude Haiku + confidence threshold) |
| 6 | Campo sentiment no handoff_queue | `data/migrations/002_p1_handoff_sentiment.sql` (P1-1) | ✅ IMPLEMENTADO (ALTER TABLE + trigger update) |

### Artefatos Adicionais Criados

| Artefato | Propósito |
|----------|-----------|
| `scripts/queue-processor.py` | Orchestrador cron (dispatch + classify + SLA) |
| `scripts/requirements.txt` | Dependências Python |
| `scripts/.env.example` | Template de variáveis de ambiente |
| Agent refs atualizados | google-maps-hunter, context-analyst, scheduler com paths corretos |

### P2 — Melhorias (Pendentes)

| # | Observação | Recomendação |
|---|-----------|-------------|
| 7 | `halt_workflow` = false quando 0 leads | Mudar para halt condicional |
| 8 | Templates referenciados mas não verificados | ✅ Verificado: 4/4 existem |
| 9 | Cron jobs comentados no schema | Descomentar quando pg_cron ativado |

---

## VEREDICTO FINAL

**Arquitetura:** 85/100 — Sólida. Veto conditions no banco, state machine unidirecional, 5 quality gates bloqueantes, handoff bidirecional com return path.

**Implementação:** 75/100 — Scripts criados para todos os gaps P0 e P1. Falta: deploy Evolution API, configurar env vars, testar end-to-end.

**Recomendação:** Atacar os 3 gaps P0 em sequência:
1. Google Maps scraper (Phase 2 funciona)
2. Website scraper (Phase 3 funciona)
3. WhatsApp dispatch (Phase 5 funciona)

Depois os 3 P1:
4. Sentiment classification (Phase 6 fica autônoma)
5. Handoff notification (zero gap de tempo)
6. Sentiment column no handoff_queue (contract completo)

---

*"A melhor coisa é você impossibilitar caminhos."*
*— Pedro Valério, 2026-02-26*
