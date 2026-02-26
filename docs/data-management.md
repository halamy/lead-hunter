# Lead Hunter - Data Management & Cleanup

## 🎯 Estratégia de Limpeza de Dados

### Problema
Leads não-respondidos acumulam no banco, aumentando custo e poluindo dados.

### Solução
**Sistema de 3 etapas:**

```
1️⃣ PRIMEIRA TENTATIVA
   Lead capturado → Mensagem enviada → Aguarda 1 dia

2️⃣ ARQUIVAMENTO
   Sem resposta após 1 dia → Arquiva → Agenda retry +3 dias úteis

3️⃣ SEGUNDA TENTATIVA
   Após 3 dias úteis → Envia retry message → Aguarda 1 dia

4️⃣ LIMPEZA FINAL
   Sem resposta no retry → DELETA permanentemente
```

---

## 🗄️ Tabelas

### `archived_leads`
**Propósito:** Armazenar leads não-respondidos para retry

**Campos principais:**
- `original_lead_id` - ID do lead original
- `company_name`, `phone`, `website` - Dados do lead
- `original_message` - Primeira mensagem enviada
- `sent_at` - Quando foi enviada
- `retry_date` - Data do retry (+3 dias úteis)
- `retry_status` - Status do retry (pending, sent, responded, failed)

### `retry_queue`
**Propósito:** Fila de mensagens de retry (segunda tentativa)

**Campos principais:**
- `archived_lead_id` - Referência ao lead arquivado
- `retry_message` - Mensagem do retry
- `scheduled_for` - Data agendada
- `response_received` - Boolean se respondeu

---

## ⚙️ Automações

### 1. `archive_non_responders()` - 23:00 (11 PM)

**O que faz:**
1. Busca leads com status `sent` sem resposta há 1+ dia
2. Copia para `archived_leads`
3. Agenda retry para +3 **dias úteis** (pula fins de semana)
4. Deleta do `leads` (limpa banco principal)

**Critérios:**
- `status = 'sent'`
- Nenhuma resposta em `lead_responses`
- Mensagem enviada há >= 1 dia

**Output:**
```sql
SELECT archive_non_responders();
-- Returns: (archived_count, retry_scheduled_count)
```

---

### 2. `process_retry_queue()` - 08:00 (8 AM)

**O que faz:**
1. Verifica `archived_leads` onde `retry_date <= TODAY`
2. Cria mensagem de retry automática
3. Adiciona à `retry_queue` com status `scheduled`

**Mensagem de retry:**
```
Oi [Empresa], tentei falar com vocês há alguns dias.
Ainda faz sentido conversarmos sobre [contexto]?
```

**Output:**
```sql
SELECT process_retry_queue();
-- Returns: retries_ready (count)
```

---

### 3. `cleanup_failed_retries()` - 23:30 (11:30 PM)

**O que faz:**
1. Busca retries enviados há 1+ dia sem resposta
2. **DELETA permanentemente** de `archived_leads` (cascades para `retry_queue`)

**Critérios:**
- Retry enviado há >= 1 dia
- `response_received = false`

**Output:**
```sql
SELECT cleanup_failed_retries();
-- Returns: deleted_count
```

---

## 📅 Timeline Exemplo

```
DIA 0 (Segunda):
  09:30 - Lead capturado
  10:15 - Mensagem enviada
  10:15 - Status: sent

DIA 1 (Terça):
  23:00 - archive_non_responders()
         → Lead arquivado
         → retry_date = Sexta (Segunda +3 dias úteis)
         → Deletado de leads

DIA 2-4 (Quarta-Sexta):
  (aguardando retry_date)

DIA 5 (Sexta):
  08:00 - process_retry_queue()
         → Retry message criada
         → Status: scheduled
  10:30 - Scheduler envia retry
         → Status: sent

DIA 6 (Sábado):
  23:30 - cleanup_failed_retries()
         → Sem resposta no retry
         → DELETADO permanentemente ✅
```

---

## 🔧 Setup

### Opção 1: pg_cron (Recomendado)

**1. Ativar extensão no Supabase:**
```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

**2. Descomentar cron jobs no schema:**
```sql
-- No arquivo supabase-schema.sql, descomentar:

SELECT cron.schedule(
  'archive-non-responders-daily',
  '0 23 * * *',
  $$SELECT archive_non_responders();$$
);

SELECT cron.schedule(
  'process-retry-queue-daily',
  '0 8 * * *',
  $$SELECT process_retry_queue();$$
);

SELECT cron.schedule(
  'cleanup-failed-retries-daily',
  '30 23 * * *',
  $$SELECT cleanup_failed_retries();$$
);
```

---

### Opção 2: Script Python (Se não tiver pg_cron)

**1. Instalar dependências:**
```bash
pip install supabase-py python-dotenv
```

**2. Configurar variáveis:**
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

**3. Executar manualmente:**
```bash
python scripts/end-of-day-cleanup.py
```

**4. Agendar com cron (Linux/Mac):**
```bash
crontab -e

# Add:
0 23 * * * /path/to/python /path/to/end-of-day-cleanup.py
```

**Ou com Task Scheduler (Windows):**
- Criar task diária às 23:00
- Action: `python C:\path\to\end-of-day-cleanup.py`

---

## 📊 Monitoramento

### Verificar estatísticas:

```sql
-- Leads ativos
SELECT COUNT(*) FROM leads;

-- Leads arquivados (aguardando retry)
SELECT COUNT(*) FROM archived_leads WHERE retry_status = 'pending';

-- Retries agendados para hoje
SELECT COUNT(*) FROM retry_queue WHERE scheduled_for = CURRENT_DATE;

-- View de pipeline
SELECT * FROM pipeline_overview;
```

### Logs de execução:

```sql
-- Últimas execuções (se usando pg_cron)
SELECT * FROM cron.job_run_details
WHERE jobname LIKE '%lead-hunter%'
ORDER BY start_time DESC
LIMIT 10;
```

---

## 🎛️ Ajustes de Timing

### Mudar dias de espera:

**Primeira tentativa (padrão: 1 dia):**
```sql
-- Em archive_non_responders(), mudar:
AND m.sent_at < (NOW() - INTERVAL '1 day')
-- Para:
AND m.sent_at < (NOW() - INTERVAL '2 days')
```

**Retry timing (padrão: +3 dias úteis):**
```sql
-- Em archive_non_responders(), mudar:
add_business_days(CURRENT_DATE, 3)
-- Para:
add_business_days(CURRENT_DATE, 5) -- +5 dias úteis
```

**Aguardar resposta do retry (padrão: 1 dia):**
```sql
-- Em cleanup_failed_retries(), mudar:
AND rq.sent_at < (NOW() - INTERVAL '1 day')
-- Para:
AND rq.sent_at < (NOW() - INTERVAL '2 days')
```

---

## ⚠️ Importante

### Backup antes de deletar:

Se quiser manter histórico completo antes de deletar:

```sql
-- Criar tabela de backup (one-time)
CREATE TABLE deleted_leads_backup AS
SELECT * FROM archived_leads LIMIT 0;

-- Modificar cleanup_failed_retries() para backup antes de deletar:
-- (adicionar INSERT INTO deleted_leads_backup antes de DELETE)
```

### Recovery:

Se deletou por engano:

```sql
-- Restaurar do backup
INSERT INTO archived_leads
SELECT * FROM deleted_leads_backup
WHERE archived_at > '2026-02-15'; -- data específica
```

---

## 🔍 Troubleshooting

### Retries não sendo agendados:

```sql
-- Verificar função
SELECT * FROM archived_leads WHERE retry_scheduled = false;
-- Se tiver registros, executar manualmente:
SELECT archive_non_responders();
```

### Dias úteis incorretos:

```sql
-- Testar função
SELECT add_business_days('2026-02-14'::date, 3);
-- Deve pular finais de semana
```

### Performance lenta:

```sql
-- Verificar indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename IN ('archived_leads', 'retry_queue');

-- Reindexar se necessário
REINDEX TABLE archived_leads;
REINDEX TABLE retry_queue;
```

---

**Documentação atualizada:** 2026-02-16
