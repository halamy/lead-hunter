-- ============================================================================
-- MIGRATION 002: P1 Fixes — Handoff Sentiment + Notification Support
-- Author: Pedro Valério (Process Absolutist)
-- Date: 2026-02-26
-- Fixes: Missing sentiment column in handoff_queue, notification tracking
-- ============================================================================
-- "Zero gap de tempo entre handoff e pickup."
-- ============================================================================

BEGIN;

-- ============================================================================
-- P1-1: ADD SENTIMENT TO HANDOFF_QUEUE
-- ============================================================================
-- Problem: Sales-closer entry-gate-checklist expects 'sentiment' field
--          but handoff_queue doesn't have it. Gatekeeper must infer.
-- Fix: Add sentiment column with default 'positive' (only positive leads
--       should reach handoff_queue via auto_create_handoff_on_response).

ALTER TABLE handoff_queue ADD COLUMN IF NOT EXISTS sentiment TEXT
  DEFAULT 'positive'
  CHECK (sentiment IN ('positive', 'interested', 'question'));

COMMENT ON COLUMN handoff_queue.sentiment IS
  'P1-1: Response sentiment. Only positive/interested/question reach handoff. Contract with sales-closer.';

-- Update the auto_create_handoff_on_response function to include sentiment
CREATE OR REPLACE FUNCTION auto_create_handoff_on_response()
RETURNS TRIGGER AS $$
DECLARE
  v_response TEXT;
  v_sentiment TEXT;
  v_context JSONB;
  v_icp_score INTEGER;
  v_outreach_msg TEXT;
  v_sent_at TIMESTAMP;
BEGIN
  -- Only fire when transitioning TO 'responded'
  IF NEW.status = 'responded' AND OLD.status != 'responded' THEN

    -- Get latest response + sentiment
    SELECT response_text, lr.sentiment INTO v_response, v_sentiment
    FROM lead_responses lr
    WHERE lr.lead_id = NEW.id
    ORDER BY lr.received_at DESC
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

    -- Get outreach message and sent_at for conversation history
    SELECT m.message_text, m.sent_at INTO v_outreach_msg, v_sent_at
    FROM messages m
    WHERE m.lead_id = NEW.id AND m.status IN ('sent', 'delivered', 'read')
    ORDER BY m.sent_at DESC
    LIMIT 1;

    -- Build lead profile and insert
    INSERT INTO handoff_queue (
      lead_id,
      lead_profile,
      context_summary,
      response_received,
      qualification_score,
      sentiment,
      conversation_starter
    ) VALUES (
      NEW.id,
      jsonb_build_object(
        'company_name', NEW.company_name,
        'phone', NEW.phone,
        'website', NEW.website,
        'address', NEW.address,
        'icp_score', NEW.icp_score,
        'outreach_message', COALESCE(v_outreach_msg, ''),
        'outreach_sent_at', v_sent_at
      ),
      COALESCE(v_context, '{}'::jsonb),
      COALESCE(v_response, ''),
      COALESCE(NEW.icp_score, 0),
      COALESCE(v_sentiment, 'positive'),
      'Lead respondeu positivamente ao primeiro contato. Retomar conversa a partir da resposta.'
    )
    ON CONFLICT (lead_id) DO UPDATE SET
      response_received = COALESCE(v_response, ''),
      sentiment = COALESCE(v_sentiment, 'positive'),
      status = 'pending',
      created_at = NOW(),
      picked_up_at = NULL,
      resolved_at = NULL;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auto_create_handoff_on_response() IS
  'P1-1: Updated to include sentiment + conversation history in handoff package.';

-- ============================================================================
-- P1-2: HANDOFF NOTIFICATION TRACKING
-- ============================================================================
-- Problem: handoff_queue gets populated but nobody notifies sales-closer.
-- Fix: Notification log table + function that can be called by Edge Function.

CREATE TABLE IF NOT EXISTS handoff_notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handoff_id UUID NOT NULL REFERENCES handoff_queue(id) ON DELETE CASCADE,
  lead_id UUID NOT NULL REFERENCES leads(id),

  -- Notification tracking
  notification_type TEXT NOT NULL DEFAULT 'new_handoff'
    CHECK (notification_type IN ('new_handoff', 'sla_warning', 'expired')),
  channel TEXT NOT NULL DEFAULT 'supabase_realtime'
    CHECK (channel IN ('supabase_realtime', 'webhook', 'edge_function')),

  -- Status
  sent_at TIMESTAMP DEFAULT NOW(),
  acknowledged_at TIMESTAMP,
  delivery_status TEXT DEFAULT 'sent'
    CHECK (delivery_status IN ('sent', 'delivered', 'acknowledged', 'failed')),

  -- Retry
  attempts INTEGER DEFAULT 1,
  last_error TEXT,

  UNIQUE(handoff_id, notification_type)
);

CREATE INDEX idx_handoff_notifications_pending
  ON handoff_notifications(delivery_status)
  WHERE delivery_status IN ('sent', 'failed');

COMMENT ON TABLE handoff_notifications IS
  'P1-2: Tracks notifications sent to sales-closer about new handoffs. Zero gap de tempo.';

-- Function: Send notification (called by Edge Function or cron)
CREATE OR REPLACE FUNCTION notify_sales_closer_new_handoff()
RETURNS TABLE(
  notifications_sent INTEGER,
  notifications_failed INTEGER
) AS $$
DECLARE
  v_sent INTEGER := 0;
  v_failed INTEGER := 0;
BEGIN
  -- Find pending handoffs without notification
  WITH unnotified AS (
    SELECT hq.id as handoff_id, hq.lead_id
    FROM handoff_queue hq
    WHERE hq.status = 'pending'
      AND NOT EXISTS (
        SELECT 1 FROM handoff_notifications hn
        WHERE hn.handoff_id = hq.id
        AND hn.notification_type = 'new_handoff'
      )
  ),
  inserted AS (
    INSERT INTO handoff_notifications (handoff_id, lead_id, notification_type, channel)
    SELECT handoff_id, lead_id, 'new_handoff', 'supabase_realtime'
    FROM unnotified
    RETURNING id
  )
  SELECT COUNT(*) INTO v_sent FROM inserted;

  RETURN QUERY SELECT v_sent, v_failed;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION notify_sales_closer_new_handoff() IS
  'P1-2: Creates notification records for unnotified handoffs. Edge Function polls this.';

-- ============================================================================
-- P1-3: HANDOFF TTL ENFORCEMENT
-- ============================================================================
-- Problem: TTL of 4h exists in schema but nothing enforces it.
-- Fix: Function to expire stale pending handoffs.

CREATE OR REPLACE FUNCTION expire_stale_handoffs(p_ttl_hours INTEGER DEFAULT 4)
RETURNS TABLE(expired_count INTEGER) AS $$
DECLARE
  v_expired INTEGER := 0;
BEGIN
  WITH expired AS (
    UPDATE handoff_queue
    SET status = 'expired',
        resolved_at = NOW()
    WHERE status = 'pending'
      AND created_at < (NOW() - (p_ttl_hours || ' hours')::INTERVAL)
    RETURNING id
  )
  SELECT COUNT(*) INTO v_expired FROM expired;

  RETURN QUERY SELECT v_expired;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION expire_stale_handoffs(INTEGER) IS
  'P1-3: Expires pending handoffs after TTL. Default 4h. Lead went cold.';

-- ============================================================================
-- P1-4: VIEWS FOR MONITORING
-- ============================================================================

-- Handoff monitoring view (for sales-closer polling)
CREATE OR REPLACE VIEW pending_handoffs AS
SELECT
  hq.id as handoff_id,
  hq.lead_id,
  hq.lead_profile ->> 'company_name' as company_name,
  hq.lead_profile ->> 'phone' as phone,
  hq.sentiment,
  hq.qualification_score,
  hq.response_received,
  hq.created_at,
  hq.ttl_hours,
  EXTRACT(EPOCH FROM (NOW() - hq.created_at)) / 3600 as hours_pending,
  CASE
    WHEN EXTRACT(EPOCH FROM (NOW() - hq.created_at)) / 3600 > hq.ttl_hours THEN 'EXPIRED'
    WHEN EXTRACT(EPOCH FROM (NOW() - hq.created_at)) / 3600 > hq.ttl_hours * 0.75 THEN 'WARNING'
    ELSE 'HEALTHY'
  END as sla_status
FROM handoff_queue hq
WHERE hq.status = 'pending'
ORDER BY hq.created_at ASC;

COMMENT ON VIEW pending_handoffs IS
  'P1-4: Monitor pending handoffs with SLA status. Used by sales-closer gatekeeper.';

-- Sentiment classification report
CREATE OR REPLACE VIEW sentiment_report AS
SELECT
  lr.sentiment,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM lead_responses lr
WHERE lr.sentiment IS NOT NULL
GROUP BY lr.sentiment
ORDER BY count DESC;

COMMENT ON VIEW sentiment_report IS
  'P1-4: Response sentiment distribution. Used by pipeline-report task.';

COMMIT;
