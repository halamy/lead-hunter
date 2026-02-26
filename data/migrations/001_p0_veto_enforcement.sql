-- ============================================================================
-- MIGRATION 001: P0 Veto Enforcement - Lead Hunter Squad
-- Author: Pedro Valério (Process Absolutist)
-- Date: 2026-02-24
-- Fixes: State transitions, dedup, rate limits, ICP alignment, handoff queue
-- ============================================================================
-- "SE executor CONSEGUE fazer errado, processo está errado."
-- This migration transforms markdown vetos into database-enforced blocks.
-- ============================================================================

BEGIN;

-- ============================================================================
-- P0-1: STATE MACHINE TRANSITION ENFORCEMENT
-- ============================================================================
-- Problem: Any agent can UPDATE leads SET status = 'responded' WHERE status = 'new'
-- Fix: Trigger function that validates OLD.status → NEW.status transitions

CREATE OR REPLACE FUNCTION enforce_lead_status_transition()
RETURNS TRIGGER AS $$
DECLARE
  valid_transitions JSONB := '{
    "new": ["context_pending", "closed"],
    "context_pending": ["ready", "context_failed", "closed"],
    "context_failed": ["ready", "closed"],
    "ready": ["sent", "closed"],
    "sent": ["delivered", "responded", "failed", "closed"],
    "delivered": ["read", "responded", "closed"],
    "read": ["responded", "closed"],
    "responded": ["closed"],
    "failed": ["ready", "closed"],
    "closed": []
  }'::jsonb;
  allowed_targets JSONB;
BEGIN
  -- Skip if status hasn't changed
  IF OLD.status = NEW.status THEN
    RETURN NEW;
  END IF;

  allowed_targets := valid_transitions -> OLD.status;

  IF allowed_targets IS NULL THEN
    RAISE EXCEPTION 'lead_status_transition_error: Unknown source status "%"', OLD.status;
  END IF;

  IF NOT allowed_targets ? NEW.status THEN
    RAISE EXCEPTION 'lead_status_transition_error: Invalid transition "%" → "%". Allowed: %',
      OLD.status, NEW.status, allowed_targets;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_lead_status_transition_trigger
  BEFORE UPDATE OF status ON leads
  FOR EACH ROW
  EXECUTE FUNCTION enforce_lead_status_transition();

COMMENT ON FUNCTION enforce_lead_status_transition() IS
  'P0-1: Enforces unidirectional state machine. Nada volta num fluxo. NUNCA.';

-- Also enforce message status transitions
CREATE OR REPLACE FUNCTION enforce_message_status_transition()
RETURNS TRIGGER AS $$
DECLARE
  valid_transitions JSONB := '{
    "queued": ["scheduled", "cancelled"],
    "scheduled": ["sent", "failed", "cancelled"],
    "sent": ["delivered", "read", "responded", "failed"],
    "delivered": ["read", "responded"],
    "read": ["responded"],
    "responded": [],
    "failed": ["queued"],
    "cancelled": []
  }'::jsonb;
  allowed_targets JSONB;
BEGIN
  IF OLD.status = NEW.status THEN
    RETURN NEW;
  END IF;

  allowed_targets := valid_transitions -> OLD.status;

  IF allowed_targets IS NULL THEN
    RAISE EXCEPTION 'message_status_transition_error: Unknown source status "%"', OLD.status;
  END IF;

  IF NOT allowed_targets ? NEW.status THEN
    RAISE EXCEPTION 'message_status_transition_error: Invalid transition "%" → "%". Allowed: %',
      OLD.status, NEW.status, allowed_targets;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_message_status_transition_trigger
  BEFORE UPDATE OF status ON messages
  FOR EACH ROW
  EXECUTE FUNCTION enforce_message_status_transition();

-- Update leads CHECK to include new states
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_status_check;
ALTER TABLE leads ADD CONSTRAINT leads_status_check CHECK (status IN (
  'new',
  'context_pending',
  'context_failed',
  'ready',
  'sent',
  'delivered',
  'read',
  'responded',
  'failed',
  'closed'
));

-- ============================================================================
-- P0-2: HANDOFF QUEUE (lead-hunter → sales-closer bridge)
-- ============================================================================
-- Problem: No trigger, no webhook, no event bus between squads.
-- Fix: handoff_queue table + auto-trigger when lead reaches 'responded'.

CREATE TABLE IF NOT EXISTS handoff_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Lead reference
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,

  -- Handoff data package (canonical contract)
  lead_profile JSONB NOT NULL,         -- company, phone, website, address, icp_score
  context_summary JSONB,               -- pain_points, services, urgency_signals
  response_received TEXT NOT NULL,      -- actual WhatsApp response text
  qualification_score INTEGER NOT NULL, -- 1-30 (aligned with ICP framework)
  conversation_starter TEXT,            -- suggested opening for sales-closer

  -- Status tracking
  status TEXT DEFAULT 'pending' CHECK (status IN (
    'pending',      -- awaiting pickup by sales-closer
    'picked_up',    -- sales-closer started processing
    'accepted',     -- gatekeeper approved
    'rejected',     -- gatekeeper rejected (see rejection_reason)
    'expired'       -- TTL exceeded, lead went cold
  )),

  -- Rejection handling (return path)
  rejection_reason TEXT,
  missing_fields TEXT[],

  -- SLA tracking
  created_at TIMESTAMP DEFAULT NOW(),
  picked_up_at TIMESTAMP,
  resolved_at TIMESTAMP,
  ttl_hours INTEGER DEFAULT 4,         -- expires if not picked up in 4h

  -- Idempotency
  UNIQUE(lead_id)
);

CREATE INDEX idx_handoff_queue_status ON handoff_queue(status);
CREATE INDEX idx_handoff_queue_pending ON handoff_queue(status, created_at)
  WHERE status = 'pending';

COMMENT ON TABLE handoff_queue IS
  'P0-2: Bridge between lead-hunter and sales-closer. Auto-populated on lead response.';

-- Auto-populate handoff_queue when lead status becomes 'responded'
CREATE OR REPLACE FUNCTION auto_create_handoff_on_response()
RETURNS TRIGGER AS $$
DECLARE
  v_response TEXT;
  v_context JSONB;
  v_icp_score INTEGER;
BEGIN
  -- Only fire when transitioning TO 'responded'
  IF NEW.status = 'responded' AND OLD.status != 'responded' THEN

    -- Get latest response
    SELECT response_text INTO v_response
    FROM lead_responses
    WHERE lead_id = NEW.id
    ORDER BY received_at DESC
    LIMIT 1;

    -- Get context
    SELECT jsonb_build_object(
      'pain_points', COALESCE(lc.pain_points, '[]'::jsonb),
      'services_offered', to_jsonb(COALESCE(lc.services_offered, '{}'::text[])),
      'urgency_signals', to_jsonb(COALESCE(lc.urgency_signals, '{}'::text[])),
      'confidence_score', lc.confidence_score
    ) INTO v_context
    FROM lead_context lc
    WHERE lc.lead_id = NEW.id;

    -- Build lead profile and insert
    INSERT INTO handoff_queue (
      lead_id,
      lead_profile,
      context_summary,
      response_received,
      qualification_score
    ) VALUES (
      NEW.id,
      jsonb_build_object(
        'company_name', NEW.company_name,
        'phone', NEW.phone,
        'website', NEW.website,
        'address', NEW.address,
        'icp_score', NEW.icp_score
      ),
      COALESCE(v_context, '{}'::jsonb),
      COALESCE(v_response, ''),
      COALESCE(NEW.icp_score, 0)
    )
    ON CONFLICT (lead_id) DO UPDATE SET
      response_received = COALESCE(v_response, ''),
      status = 'pending',
      created_at = NOW(),
      picked_up_at = NULL,
      resolved_at = NULL;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_handoff_on_response_trigger
  AFTER UPDATE OF status ON leads
  FOR EACH ROW
  EXECUTE FUNCTION auto_create_handoff_on_response();

COMMENT ON FUNCTION auto_create_handoff_on_response() IS
  'P0-2: Auto-creates handoff entry when lead reaches responded. Zero gap de tempo.';

-- ============================================================================
-- P0-3: UNIQUE CONSTRAINT ON PHONE (Deduplication)
-- ============================================================================
-- Problem: leads.phone has INDEX but not UNIQUE. Duplicates slip through.
-- Fix: UNIQUE constraint. ON CONFLICT gives controlled behavior.
-- Note: We use a partial unique index to allow closed leads with same phone.

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_phone_unique_active
  ON leads(phone)
  WHERE status NOT IN ('closed');

COMMENT ON INDEX idx_leads_phone_unique_active IS
  'P0-3: Prevents duplicate active leads with same phone. Closed leads can share phone for re-entry.';

-- ============================================================================
-- P0-4: RATE LIMITING TABLE + CHECK FUNCTION
-- ============================================================================
-- Problem: 30/hr and 200/day are documentation. Zero enforcement.
-- Fix: rate_limit_log table + check function called before every send.

CREATE TABLE IF NOT EXISTS rate_limit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  action_type TEXT NOT NULL DEFAULT 'whatsapp_send',
  executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  batch_id UUID,
  lead_id UUID REFERENCES leads(id)
);

CREATE INDEX idx_rate_limit_executed ON rate_limit_log(executed_at DESC);
CREATE INDEX idx_rate_limit_action ON rate_limit_log(action_type, executed_at DESC);

-- Function: Check rate limits BEFORE sending
CREATE OR REPLACE FUNCTION check_rate_limit(
  p_action_type TEXT DEFAULT 'whatsapp_send',
  p_max_per_hour INTEGER DEFAULT 30,
  p_max_per_day INTEGER DEFAULT 200
)
RETURNS TABLE(
  allowed BOOLEAN,
  current_hour_count INTEGER,
  current_day_count INTEGER,
  reason TEXT
) AS $$
DECLARE
  v_hour_count INTEGER;
  v_day_count INTEGER;
BEGIN
  -- Count actions in last hour
  SELECT COUNT(*) INTO v_hour_count
  FROM rate_limit_log
  WHERE action_type = p_action_type
    AND executed_at > (NOW() - INTERVAL '1 hour');

  -- Count actions today
  SELECT COUNT(*) INTO v_day_count
  FROM rate_limit_log
  WHERE action_type = p_action_type
    AND executed_at::date = CURRENT_DATE;

  -- Check limits
  IF v_hour_count >= p_max_per_hour THEN
    RETURN QUERY SELECT false, v_hour_count, v_day_count,
      format('RATE_LIMIT_HOUR: %s/%s per hour reached', v_hour_count, p_max_per_hour);
    RETURN;
  END IF;

  IF v_day_count >= p_max_per_day THEN
    RETURN QUERY SELECT false, v_hour_count, v_day_count,
      format('RATE_LIMIT_DAY: %s/%s per day reached', v_day_count, p_max_per_day);
    RETURN;
  END IF;

  RETURN QUERY SELECT true, v_hour_count, v_day_count, 'OK'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Function: Log a send action (call AFTER successful send)
CREATE OR REPLACE FUNCTION log_rate_limit_action(
  p_action_type TEXT DEFAULT 'whatsapp_send',
  p_lead_id UUID DEFAULT NULL,
  p_batch_id UUID DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO rate_limit_log (action_type, lead_id, batch_id)
  VALUES (p_action_type, p_lead_id, p_batch_id);
END;
$$ LANGUAGE plpgsql;

-- Trigger: Block message_queue processing if rate limit exceeded
CREATE OR REPLACE FUNCTION enforce_rate_limit_on_queue()
RETURNS TRIGGER AS $$
DECLARE
  v_allowed BOOLEAN;
  v_reason TEXT;
BEGIN
  -- Only check when transitioning to 'processing' (about to send)
  IF NEW.status = 'processing' AND OLD.status = 'pending' THEN
    SELECT allowed, reason INTO v_allowed, v_reason
    FROM check_rate_limit('whatsapp_send', 30, 200);

    IF NOT v_allowed THEN
      RAISE EXCEPTION 'rate_limit_exceeded: %. Message queued but NOT sent.', v_reason;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_rate_limit_trigger
  BEFORE UPDATE OF status ON message_queue
  FOR EACH ROW
  EXECUTE FUNCTION enforce_rate_limit_on_queue();

-- Trigger: Enforce business hours (9h-17h BRT) on queue processing
CREATE OR REPLACE FUNCTION enforce_business_hours_on_queue()
RETURNS TRIGGER AS $$
DECLARE
  v_current_hour INTEGER;
BEGIN
  -- Only check when transitioning to 'processing'
  IF NEW.status = 'processing' AND OLD.status = 'pending' THEN
    -- Get current hour in BRT (UTC-3)
    v_current_hour := EXTRACT(HOUR FROM (NOW() AT TIME ZONE 'America/Sao_Paulo'));

    IF v_current_hour < 9 OR v_current_hour >= 17 THEN
      RAISE EXCEPTION 'business_hours_violation: Current time is %h BRT. Sending allowed only 9h-17h.',
        v_current_hour;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_business_hours_trigger
  BEFORE UPDATE OF status ON message_queue
  FOR EACH ROW
  EXECUTE FUNCTION enforce_business_hours_on_queue();

COMMENT ON TABLE rate_limit_log IS
  'P0-4: Rate limiting enforcement. 30/hr, 200/day. Physical block, not documentation.';
COMMENT ON FUNCTION check_rate_limit(TEXT, INTEGER, INTEGER) IS
  'P0-4: Check if action is within rate limits. Call BEFORE sending.';
COMMENT ON FUNCTION enforce_rate_limit_on_queue() IS
  'P0-4: Blocks queue processing if rate limit exceeded. HARD VETO.';
COMMENT ON FUNCTION enforce_business_hours_on_queue() IS
  'P0-4: Blocks sends outside 9h-17h BRT. HARD VETO.';

-- ============================================================================
-- P0-6: ICP SCORE ALIGNMENT (1-10 → 1-30)
-- ============================================================================
-- Problem: Agent documents 6 dimensions × 5 points = 30. DB has CHECK (1-10).
-- Fix: Expand to 1-30 + add icp_dimensions JSONB + threshold column.

ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_icp_score_check;
ALTER TABLE leads ADD CONSTRAINT leads_icp_score_check
  CHECK (icp_score BETWEEN 1 AND 30);

-- Add ICP dimensions breakdown
ALTER TABLE leads ADD COLUMN IF NOT EXISTS icp_dimensions JSONB;
-- Expected format: {"market_fit": 5, "budget_potential": 4, "decision_maker": 3,
--                    "urgency": 4, "digital_presence": 5, "location_fit": 3}

-- Add context_retry_count (was referenced in agents but missing from schema)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS context_retry_count INTEGER DEFAULT 0;

COMMENT ON COLUMN leads.icp_score IS
  'P0-6: ICP score on 30-point scale (6 dimensions × 5 points). Threshold: 21/30 for qualification.';
COMMENT ON COLUMN leads.icp_dimensions IS
  'P0-6: Breakdown of ICP score by dimension. Each dimension scored 1-5.';
COMMENT ON COLUMN leads.context_retry_count IS
  'P0-6: Context extraction retry counter. Hard ceiling: 3.';

-- Enforce ICP threshold before advancing to google-maps-hunter phase
CREATE OR REPLACE FUNCTION enforce_icp_threshold()
RETURNS TRIGGER AS $$
BEGIN
  -- When moving from 'new' to 'context_pending', ICP must be scored >= 21
  IF NEW.status = 'context_pending' AND OLD.status = 'new' THEN
    IF NEW.icp_score IS NULL OR NEW.icp_score < 21 THEN
      RAISE EXCEPTION 'icp_threshold_veto: ICP score % is below threshold 21/30. Lead not qualified.',
        COALESCE(NEW.icp_score::text, 'NULL');
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_icp_threshold_trigger
  BEFORE UPDATE OF status ON leads
  FOR EACH ROW
  EXECUTE FUNCTION enforce_icp_threshold();

-- ============================================================================
-- CLEANUP: Ensure message personalization minimum
-- ============================================================================
-- Problem: personalization_score CHECK allows 1-10 but veto says >= 7
-- Fix: Add constraint on message_queue (can't queue low-quality messages)

CREATE OR REPLACE FUNCTION enforce_personalization_minimum()
RETURNS TRIGGER AS $$
DECLARE
  v_score INTEGER;
BEGIN
  -- Check personalization score of associated message
  SELECT personalization_score INTO v_score
  FROM messages WHERE id = NEW.message_id;

  IF v_score IS NOT NULL AND v_score < 5 THEN
    RAISE EXCEPTION 'personalization_veto: Score %/10 is below minimum 5. Re-craft required.',
      v_score;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_personalization_trigger
  BEFORE INSERT ON message_queue
  FOR EACH ROW
  EXECUTE FUNCTION enforce_personalization_minimum();

-- ============================================================================
-- HANDOFF REJECTIONS TABLE (return path from sales-closer gatekeeper)
-- ============================================================================

CREATE TABLE IF NOT EXISTS handoff_rejections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handoff_id UUID NOT NULL REFERENCES handoff_queue(id) ON DELETE CASCADE,
  lead_id UUID NOT NULL REFERENCES leads(id),

  -- Rejection details
  rejection_reason TEXT NOT NULL,
  missing_fields TEXT[],
  gatekeeper_score INTEGER,           -- re-qualification score from gatekeeper
  recommended_action TEXT,            -- 'enrich_context', 're_qualify', 'archive'

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN (
    'pending',      -- awaiting lead-hunter processing
    'acknowledged', -- lead-hunter saw it
    'resolved',     -- lead-hunter fixed and re-submitted
    'archived'      -- lead abandoned
  )),

  created_at TIMESTAMP DEFAULT NOW(),
  resolved_at TIMESTAMP,

  UNIQUE(handoff_id)
);

CREATE INDEX idx_handoff_rejections_pending ON handoff_rejections(status)
  WHERE status = 'pending';

COMMENT ON TABLE handoff_rejections IS
  'P0-2: Return path from sales-closer gatekeeper. Zero gap de tempo no feedback.';

COMMIT;
