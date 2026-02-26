# Lead Hunter Squad — Claude Code Configuration

## Squad Identity

- **Name:** Lead Hunter
- **Purpose:** Automated lead generation from Google Maps with personalized WhatsApp outreach
- **Version:** 1.0.0
- **Fidelity:** 60-75% (web research-based)

## Agent Hierarchy

| Tier | Agent | Role |
|------|-------|------|
| Orchestrator | `hunter-chief` | Coordena squad, gerencia estado via Supabase |
| Tier 0 | `lead-qualifier` | Define ICP, qualifica requests (30-point scoring) |
| Tier 1 | `google-maps-hunter` | Captura leads do Google Maps |
| Tier 1 | `message-crafter` | Cria mensagens personalizadas (Hormozi + Halbert) |
| Tier 2 | `context-analyst` | Extrai contexto dos websites |
| Tier 2 | `database-manager` | Gerencia Supabase (schema, queries, integridade) |
| Tier 2 | `scheduler` | Agenda e dispara mensagens (9h-17h BRT) |

## Elite Minds

| Mind | Framework | Application |
|------|-----------|-------------|
| Aaron Ross | Predictable Revenue, Cold Calling 2.0 | Lead generation process |
| Jeb Blount | Fanatical Prospecting | Multi-channel approach |
| Alex Hormozi | $100M Offers, Value Equation | Message personalization |
| Gary Halbert | Direct Response Copywriting | Cold message crafting |
| Trish Bertuzzi | Sales Development Playbook | Lead qualification |

## Hard Rules (Inviolable)

1. **Rate Limits:** Max 30 msgs/hour, 200/day — NEVER exceed
2. **Time Window:** 9h-17h BRT only — HARD BLOCK outside
3. **Phone Required:** Lead without phone = auto-skip (GMH_001)
4. **ICP Gate:** Score < 21/30 = BLOCK capture
5. **Personalization:** Score < 5/10 = REJECT message
6. **Unidirectional Flow:** Lead status NEVER goes backwards
7. **Closed-Lost:** HARD BLOCK reentry — zero contact posterior
8. **Random Delays:** 30-180s between messages — anti-detection

## State Machine

```
new → context_pending → ready → sent → responded → closed
                                  ↓
                            closed-lost (terminal)
```

**Transitions enforced at database level** (trigger `enforce_lead_status_transition`).

## Workflow: WF-Lead-Capture

```
Phase 1: ICP Definition (lead-qualifier) → Checkpoint: human review
Phase 2: Lead Capture (google-maps-hunter) → Checkpoint: auto
Phase 3: Context Extraction (context-analyst) → Checkpoint: auto
Phase 4: Message Crafting (message-crafter) → Checkpoint: human review
Phase 5: Dispatch (scheduler) → Checkpoint: auto
Phase 6: Response Monitor (hunter-chief) → Checkpoint: auto
```

## Supabase Tables

- `leads` — Core lead data
- `lead_context` — Website intelligence
- `messages` — Crafted messages
- `lead_responses` — Incoming responses
- `message_queue` — Dispatch schedule
- `archived_leads` — Non-responders
- `retry_queue` — Second-attempt messages

## Handoff

- **Next Squad:** `sales-closer`
- **Trigger:** `lead_responded == true && sentiment == positive`
- **Package:** lead_profile + context_summary + response + qualification_score

## File Structure

```
lead-hunter/
├── agents/          # 7 agent definitions
├── tasks/           # 7 task definitions
├── workflows/       # 1 main workflow (wf-lead-capture)
├── checklists/      # Quality gates and validation
├── templates/       # Reusable templates (messages, ICP, handoff, reports)
├── data/            # Supabase schema + migrations
├── docs/            # Documentation
├── scripts/         # Automation scripts
├── config.yaml      # Squad configuration
└── README.md        # Main documentation
```

## Development Commands

- `*capture-leads "{keywords}" "{location}" {count}` — Start lead capture
- `*status` — Pipeline status from Supabase
- `*check-responses` — Check WhatsApp responses
- `*pipeline-report` — Full metrics report
- `*handoff-ready` — List leads ready for sales-closer

## Quality Gates

| Gate | Checklist | When |
|------|-----------|------|
| ICP Validation | `checklists/lead-qualification-checklist.md` | Before capture |
| Message Quality | `checklists/message-quality-checklist.md` | Before dispatch |
| Dispatch Safety | `checklists/dispatch-safety-checklist.md` | Before sending |
| Pipeline Health | `checklists/pipeline-health-checklist.md` | Daily report |
| Handoff Readiness | `checklists/handoff-readiness-checklist.md` | Before sales-closer |
