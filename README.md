# Lead Hunter Squad

> **Automated lead generation from Google Maps with personalized WhatsApp outreach**

## 🎯 Propósito

Capturar leads do Google Maps, extrair contexto dos websites, criar mensagens personalizadas e enviar via WhatsApp API (não oficial) respeitando horário comercial (9h-17h) e rate limits.

## 👥 Agents

### Orchestrator
- **Hunter Chief** - Coordena squad, gerencia estado via Supabase

### Tier 0 (Diagnosis)
- **Lead Qualifier** - Define ICP, qualifica requests, valida critérios

### Tier 1 (Masters - Execution)
- **Google Maps Hunter** - Captura leads do Google Maps (nome, telefone, site, endereço)
- **Message Crafter** - Cria mensagens personalizadas baseadas em contexto

### Tier 2 (Systematizers - Support)
- **Context Analyst** - Extrai contexto e inteligência dos websites
- **Database Manager** - Gerencia Supabase (schema, queries, integridade)
- **Scheduler** - Agenda e dispara mensagens (9h-17h, delays randômicos)

## 🧠 Elite Minds (Base de Conhecimento)

| Mind | Framework | Aplicação |
|------|-----------|-----------|
| **Aaron Ross** | Predictable Revenue, Cold Calling 2.0 | Lead generation process |
| **Jeb Blount** | Fanatical Prospecting | Multi-channel approach |
| **Alex Hormozi** | $100M Offers, Value Equation | Message personalization |
| **Gary Halbert** | Direct Response Copywriting | Cold message crafting |
| **Trish Bertuzzi** | Sales Development Playbook | Lead qualification |

## 🗄️ Supabase Integration

**Database central para todo o squad:**

- `leads` - Leads capturados do Google Maps
- `lead_context` - Contexto extraído dos websites
- `messages` - Mensagens enviadas via WhatsApp
- `lead_responses` - Respostas recebidas dos leads
- `message_queue` - Fila de agendamento (9h-17h)
- `archived_leads` - ⭐ **NOVO:** Leads não-respondidos (retry após 3 dias úteis)
- `retry_queue` - ⭐ **NOVO:** Segunda tentativa de contato

**Schema:** Ver `data/supabase-schema.sql`

### 🧹 Data Management (Automático)

**Sistema de limpeza inteligente:**

```
1️⃣ Sem resposta após 1 dia → Arquiva
2️⃣ Aguarda 3 dias úteis → Retry automático
3️⃣ Sem resposta no retry → DELETA (limpa banco)
```

**Documentação:** Ver `docs/data-management.md`

## ⏰ Automação

### Horário Comercial
- **Envio apenas:** 9h-17h
- **Timezone:** America/Sao_Paulo

### Rate Limiting (API WhatsApp não oficial)
- **Max por hora:** 30 mensagens
- **Max por dia:** 200 mensagens

### Anti-Detecção
- **Delays randômicos:** 30-180 segundos entre mensagens
- **Distribuição:** Throughout the day (não todas às 9h)
- **Mimic human:** Irregular patterns

## 🔄 Workflow Típico

```
1. User define ICP → Lead Qualifier
2. Google Maps Hunter → captura leads → save Supabase
3. Context Analyst → extrai contexto dos sites → save Supabase
4. Message Crafter → cria mensagem personalizada → save Supabase
5. Scheduler → agenda envio (9h-17h) → WhatsApp API
6. Response Tracker → monitora respostas → save Supabase
7. IF response → Handoff to Sales Closer Squad
```

## 🚀 Como Usar

### Capturar Leads

```
@lead-hunter:hunter-chief

*capture-leads "agência de marketing digital" "São Paulo, SP" 50
```

### Checar Status

```
*status
```

### Ver Respostas

```
*check-responses
```

### Pipeline Report

```
*pipeline-report
```

## 🤝 Handoff para Sales Closer

Quando lead responde positivamente, handoff automático para **Sales Closer Squad** com:

- Lead profile completo
- Conversation starter (primeira mensagem)
- Response received (resposta do lead)
- Context summary (contexto extraído)
- Qualification score

## 📊 Métricas

**Trackadas automaticamente no Supabase:**

- Leads capturados / dia
- Context extraction rate
- Mensagens enviadas / dia
- Response rate
- Handoff ready count

## ⚙️ Configuração

Ver `config.yaml` para:
- Time windows
- Rate limits
- Randomization settings
- Supabase tables
- Handoff configuration

## 🔧 Próximos Passos

1. **Setup Supabase:** Executar `data/supabase-schema.sql`
2. **Configure API:** WhatsApp API credentials
3. **Test flow:** Capturar 5-10 leads teste
4. **Monitor:** Use `*status` para acompanhar
5. **Iterate:** Ajustar ICP e mensagens baseado em response rate

## 🎓 Upgrade Path

Este squad foi criado com **web research** (fidelidade 60-75%).

Para upgrade para **85-95% fidelidade:**
- Adicionar materiais de voz dos elite minds
- Re-extrair frameworks mais profundos
- Enriquecer voice DNA com long-form content

---

**Squad Version:** 1.0.0
**Created:** 2026-02-16
**Author:** Metano[IA]
**Fidelidade:** 60-75% (web research)
