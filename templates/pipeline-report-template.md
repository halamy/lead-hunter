# Pipeline Report Template

**Purpose:** Template para relatório diário de pipeline do Lead Hunter squad.
**Owner:** hunter-chief
**Trigger:** Daily at 17:00 BRT (auto-trigger LH_AT_005) or on-demand via `*pipeline-report`
**Quality Gate:** `checklists/pipeline-health-checklist.md`

---

## Report Structure

```
═══════════════════════════════════════════════════════
  LEAD HUNTER — Pipeline Report
  Data: {YYYY-MM-DD}
  Gerado: {HH:MM} BRT
═══════════════════════════════════════════════════════

RESUMO EXECUTIVO
────────────────
Status Geral: {HEALTHY | WARNING | CRITICAL}
Campanha: {nome_da_campanha}
ICP: {industry} em {location}

MÉTRICAS DE CAPTURA
────────────────────
Leads capturados (hoje):    {N}
Leads capturados (total):   {N}
Target da campanha:         {N}
Progresso:                  {N}% ████████░░

PIPELINE STATUS
───────────────
| Status          | Count | % do Total |
|─────────────────|───────|────────────|
| new             | {N}   | {%}        |
| context_pending | {N}   | {%}        |
| ready           | {N}   | {%}        |
| sent            | {N}   | {%}        |
| responded       | {N}   | {%}        |
| closed-lost     | {N}   | {%}        |
| archived        | {N}   | {%}        |
|─────────────────|───────|────────────|
| TOTAL           | {N}   | 100%       |

EXTRAÇÃO DE CONTEXTO
─────────────────────
Leads com website:          {N}/{total}
Contexto extraído:          {N}/{com_website} ({%})
Pain points identificados:  {N} (média {X}/lead)
Extraction failures:        {N}

MENSAGENS
─────────
Mensagens criadas:          {N}
Personalization média:      {X}/10
Na fila (scheduled):        {N}
Enviadas hoje:              {N}
Enviadas total:             {N}
Failed deliveries:          {N}

RATE LIMITS
───────────
Hourly atual:               {N}/30
Daily atual:                {N}/200
Delay médio:                {N}s (target: 30-180s)
Violações:                  {N}

RESPOSTAS
─────────
Respostas recebidas:        {N}
Response rate:              {%}
  - Positive:               {N} ({%})
  - Negative:               {N} ({%})
  - Neutral:                {N} ({%})
  - Unclear:                {N} ({%})
Tempo médio de resposta:    {duration}

HANDOFFS
────────
Handoffs para sales-closer: {N}
Handoff packages completos: {N}/{total_handoffs}
Pendentes (em fila):        {N}

CLEANUP & RETRY
───────────────
Arquivados (sem resposta):  {N}
Na fila de retry:           {N}
Retries enviados:           {N}
Retries com resposta:       {N}
Deletados (cleanup final):  {N}

ALERTAS
───────
{lista_de_alertas_ou_"Nenhum alerta."}

Exemplos:
⚠️ Context extraction rate abaixo de 80% (atual: {%})
⚠️ {N} leads stuck em status '{status}' há mais de 24h
🔴 Rate limit violation detectada às {HH:MM}
🔴 {N} respostas não processadas há mais de 4h

PRÓXIMAS AÇÕES
──────────────
1. {ação_1}
2. {ação_2}
3. {ação_3}

═══════════════════════════════════════════════════════
  Relatório gerado automaticamente por hunter-chief
  Checklist: pipeline-health-checklist.md
═══════════════════════════════════════════════════════
```

---

## Data Sources (Supabase Queries)

### Pipeline Status

```sql
SELECT status, COUNT(*) as count,
  ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 1) as percentage
FROM leads
GROUP BY status
ORDER BY CASE status
  WHEN 'new' THEN 1
  WHEN 'context_pending' THEN 2
  WHEN 'ready' THEN 3
  WHEN 'sent' THEN 4
  WHEN 'responded' THEN 5
  WHEN 'closed-lost' THEN 6
END;
```

### Today's Metrics

```sql
-- Leads captured today
SELECT COUNT(*) FROM leads
WHERE captured_at >= CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo';

-- Messages sent today
SELECT COUNT(*) FROM messages
WHERE sent_at >= CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo'
  AND status = 'sent';

-- Response rate
SELECT
  COUNT(*) FILTER (WHERE lr.id IS NOT NULL) as responses,
  COUNT(*) as total_sent,
  ROUND(COUNT(*) FILTER (WHERE lr.id IS NOT NULL)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as rate
FROM messages m
LEFT JOIN lead_responses lr ON lr.lead_id = m.lead_id
WHERE m.status = 'sent';
```

### Rate Limit Check

```sql
-- Current hour count
SELECT COUNT(*) FROM messages
WHERE sent_at >= date_trunc('hour', NOW() AT TIME ZONE 'America/Sao_Paulo')
  AND status = 'sent';

-- Current day count
SELECT COUNT(*) FROM messages
WHERE sent_at >= CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo'
  AND status = 'sent';
```

---

## Conditional Sections

| Section | Show When |
|---------|-----------|
| ALERTAS | Any threshold breached |
| CLEANUP & RETRY | archived_leads or retry_queue have records |
| RATE LIMIT violations | Any violation detected |

---

## Idempotency

- Report generated once per day per campaign
- `idempotency_key`: `{campaign_id}_{YYYY-MM-DD}`
- Re-running produces same report (snapshot-based)
- On-demand via `*pipeline-report` bypasses daily limit

---

**Template Version:** 1.0.0
**Created:** 2026-02-25
**Squad:** lead-hunter
**Auto-trigger:** LH_AT_005 (daily 17:00 BRT)
