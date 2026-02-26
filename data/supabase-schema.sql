-- Lead Hunter Squad - Supabase Schema
-- Version: 1.0.0
-- Author: Metano[IA]

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: leads
-- ============================================================================
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Lead data (from Google Maps)
  company_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  website TEXT,
  address TEXT,
  google_maps_url TEXT,

  -- Metadata
  source TEXT DEFAULT 'google_maps',
  icp_score INTEGER CHECK (icp_score BETWEEN 1 AND 10),

  -- State machine
  status TEXT DEFAULT 'new' CHECK (status IN (
    'new',
    'context_pending',
    'ready',
    'sent',
    'responded',
    'closed'
  )),

  -- Timestamps
  captured_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Ownership
  created_by TEXT DEFAULT 'lead-hunter'
);

-- Indexes
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_captured_at ON leads(captured_at DESC);
CREATE INDEX idx_leads_phone ON leads(phone);

-- ============================================================================
-- TABLE: lead_context
-- ============================================================================
CREATE TABLE IF NOT EXISTS lead_context (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,

  -- Extracted data
  pain_points JSONB DEFAULT '[]'::jsonb,
  services_offered TEXT[],
  company_size TEXT,
  tech_stack TEXT[],

  -- Intelligence
  urgency_signals TEXT[],
  budget_signals TEXT[],

  -- Metadata
  scraped_at TIMESTAMP DEFAULT NOW(),
  confidence_score INTEGER CHECK (confidence_score BETWEEN 1 AND 10),

  UNIQUE(lead_id)
);

-- Index
CREATE INDEX idx_context_lead_id ON lead_context(lead_id);

-- ============================================================================
-- TABLE: messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,

  -- Message data
  message_text TEXT NOT NULL,
  personalization_score INTEGER CHECK (personalization_score BETWEEN 1 AND 10),

  -- Scheduling
  scheduled_for TIMESTAMP,
  sent_at TIMESTAMP,

  -- Status
  status TEXT DEFAULT 'queued' CHECK (status IN (
    'queued',
    'scheduled',
    'sent',
    'delivered',
    'read',
    'responded',
    'failed'
  )),

  -- WhatsApp API
  whatsapp_message_id TEXT,
  error_message TEXT,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_messages_lead_id ON messages(lead_id);
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_sent_at ON messages(sent_at DESC);

-- ============================================================================
-- TABLE: lead_responses
-- ============================================================================
CREATE TABLE IF NOT EXISTS lead_responses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  message_id UUID REFERENCES messages(id),

  -- Response data
  response_text TEXT NOT NULL,
  sentiment TEXT CHECK (sentiment IN (
    'positive',
    'neutral',
    'negative',
    'interested',
    'not_interested'
  )),

  -- Timing
  received_at TIMESTAMP DEFAULT NOW(),

  -- Next action
  needs_handoff BOOLEAN DEFAULT false,
  handoff_reason TEXT
);

-- Indexes
CREATE INDEX idx_responses_lead_id ON lead_responses(lead_id);
CREATE INDEX idx_responses_received_at ON lead_responses(received_at DESC);
CREATE INDEX idx_responses_needs_handoff ON lead_responses(needs_handoff) WHERE needs_handoff = true;

-- ============================================================================
-- TABLE: message_queue
-- ============================================================================
CREATE TABLE IF NOT EXISTS message_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lead_id UUID NOT NULL REFERENCES leads(id),
  message_id UUID NOT NULL REFERENCES messages(id),

  -- Scheduling
  scheduled_time TIMESTAMP NOT NULL,
  priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

  -- Constraints
  time_window_start TIME DEFAULT '09:00:00',
  time_window_end TIME DEFAULT '17:00:00',

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN (
    'pending',
    'processing',
    'sent',
    'failed',
    'cancelled'
  )),
  attempts INTEGER DEFAULT 0,

  -- Rate limiting
  batch_id UUID,
  delay_seconds INTEGER DEFAULT 60,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_queue_status ON message_queue(status);
CREATE INDEX idx_queue_scheduled_time ON message_queue(scheduled_time);
CREATE INDEX idx_queue_pending ON message_queue(status, scheduled_time)
  WHERE status = 'pending';

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for leads table
CREATE TRIGGER update_leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS (useful queries)
-- ============================================================================

-- Pipeline overview
CREATE OR REPLACE VIEW pipeline_overview AS
SELECT
  status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM leads
GROUP BY status
ORDER BY
  CASE status
    WHEN 'new' THEN 1
    WHEN 'context_pending' THEN 2
    WHEN 'ready' THEN 3
    WHEN 'sent' THEN 4
    WHEN 'responded' THEN 5
    WHEN 'closed' THEN 6
  END;

-- Today's activity
CREATE OR REPLACE VIEW todays_activity AS
SELECT
  COUNT(DISTINCT l.id) FILTER (WHERE l.captured_at::date = CURRENT_DATE) as leads_captured_today,
  COUNT(DISTINCT m.id) FILTER (WHERE m.sent_at::date = CURRENT_DATE) as messages_sent_today,
  COUNT(DISTINCT r.id) FILTER (WHERE r.received_at::date = CURRENT_DATE) as responses_received_today
FROM leads l
LEFT JOIN messages m ON m.lead_id = l.id
LEFT JOIN lead_responses r ON r.lead_id = l.id;

-- Leads ready for handoff
CREATE OR REPLACE VIEW leads_ready_for_handoff AS
SELECT
  l.id,
  l.company_name,
  l.phone,
  l.website,
  r.response_text,
  r.sentiment,
  r.received_at
FROM leads l
INNER JOIN lead_responses r ON r.lead_id = l.id
WHERE r.needs_handoff = true
  AND l.status = 'responded'
ORDER BY r.received_at DESC;

-- ============================================================================
-- TABLE: archived_leads (NON-RESPONDERS - First attempt failed)
-- ============================================================================
CREATE TABLE IF NOT EXISTS archived_leads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Original lead data (copied from leads)
  original_lead_id UUID NOT NULL,
  company_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  website TEXT,
  address TEXT,
  google_maps_url TEXT,

  -- Context snapshot
  pain_points JSONB,
  context_summary TEXT,

  -- Original attempt data
  original_message TEXT,
  sent_at TIMESTAMP,

  -- Archive metadata
  archived_at TIMESTAMP DEFAULT NOW(),
  archive_reason TEXT DEFAULT 'no_response',
  days_waited INTEGER DEFAULT 1, -- Days since first message

  -- Retry tracking
  retry_scheduled BOOLEAN DEFAULT false,
  retry_date DATE, -- Will be sent_at + 3 business days
  retry_status TEXT CHECK (retry_status IN (
    'pending',
    'scheduled',
    'sent',
    'responded',
    'failed'
  ))
);

-- Indexes
CREATE INDEX idx_archived_leads_retry_scheduled ON archived_leads(retry_scheduled) WHERE retry_scheduled = true;
CREATE INDEX idx_archived_leads_retry_date ON archived_leads(retry_date);
CREATE INDEX idx_archived_leads_archived_at ON archived_leads(archived_at DESC);

-- ============================================================================
-- TABLE: retry_queue (SECOND ATTEMPT - After 3 business days)
-- ============================================================================
CREATE TABLE IF NOT EXISTS retry_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  archived_lead_id UUID NOT NULL REFERENCES archived_leads(id) ON DELETE CASCADE,

  -- Retry message
  retry_message TEXT NOT NULL,
  scheduled_for DATE NOT NULL,

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN (
    'pending',
    'scheduled',
    'sent',
    'responded',
    'failed'
  )),

  -- Timing
  created_at TIMESTAMP DEFAULT NOW(),
  sent_at TIMESTAMP,

  -- Response tracking
  response_received BOOLEAN DEFAULT false,
  response_text TEXT
);

-- Indexes
CREATE INDEX idx_retry_queue_status ON retry_queue(status);
CREATE INDEX idx_retry_queue_scheduled_for ON retry_queue(scheduled_for);
CREATE INDEX idx_retry_queue_pending ON retry_queue(status, scheduled_for)
  WHERE status = 'pending';

-- ============================================================================
-- FUNCTIONS: DATA MANAGEMENT AUTOMATION
-- ============================================================================

-- Function: Calculate next business day (skip weekends)
CREATE OR REPLACE FUNCTION add_business_days(start_date DATE, days_to_add INTEGER)
RETURNS DATE AS $$
DECLARE
  result_date DATE := start_date;
  days_added INTEGER := 0;
BEGIN
  WHILE days_added < days_to_add LOOP
    result_date := result_date + INTERVAL '1 day';
    -- Skip weekends (6=Saturday, 0=Sunday)
    IF EXTRACT(DOW FROM result_date) NOT IN (0, 6) THEN
      days_added := days_added + 1;
    END IF;
  END LOOP;
  RETURN result_date;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function: Archive non-responders (run end-of-day)
CREATE OR REPLACE FUNCTION archive_non_responders()
RETURNS TABLE(
  archived_count INTEGER,
  retry_scheduled_count INTEGER
) AS $$
DECLARE
  v_archived_count INTEGER := 0;
  v_retry_count INTEGER := 0;
BEGIN
  -- Archive leads that were sent but didn't respond
  -- Criteria: status='sent', no responses, message sent >= 1 day ago

  WITH leads_to_archive AS (
    SELECT
      l.id as lead_id,
      l.company_name,
      l.phone,
      l.website,
      l.address,
      l.google_maps_url,
      lc.pain_points,
      lc.services_offered::text as context_summary,
      m.message_text as original_message,
      m.sent_at,
      EXTRACT(DAY FROM (NOW() - m.sent_at)) as days_since_sent
    FROM leads l
    INNER JOIN messages m ON m.lead_id = l.id AND m.status = 'sent'
    LEFT JOIN lead_context lc ON lc.lead_id = l.id
    LEFT JOIN lead_responses r ON r.lead_id = l.id
    WHERE l.status = 'sent'
      AND r.id IS NULL -- No responses
      AND m.sent_at < (NOW() - INTERVAL '1 day') -- At least 1 day ago
    ORDER BY m.sent_at ASC
  ),
  inserted_archives AS (
    INSERT INTO archived_leads (
      original_lead_id,
      company_name,
      phone,
      website,
      address,
      google_maps_url,
      pain_points,
      context_summary,
      original_message,
      sent_at,
      days_waited,
      retry_scheduled,
      retry_date,
      retry_status
    )
    SELECT
      lead_id,
      company_name,
      phone,
      website,
      address,
      google_maps_url,
      pain_points,
      context_summary,
      original_message,
      sent_at,
      days_since_sent::INTEGER,
      true, -- Schedule retry
      add_business_days(CURRENT_DATE, 3), -- +3 business days
      'pending'
    FROM leads_to_archive
    RETURNING id
  )
  SELECT COUNT(*) INTO v_archived_count FROM inserted_archives;

  -- Delete archived leads from main table
  DELETE FROM leads
  WHERE id IN (
    SELECT original_lead_id FROM archived_leads
    WHERE archived_at >= (NOW() - INTERVAL '1 minute')
  );

  -- Count retry queue entries created
  SELECT COUNT(*) INTO v_retry_count
  FROM archived_leads
  WHERE archived_at >= (NOW() - INTERVAL '1 minute')
    AND retry_scheduled = true;

  RETURN QUERY SELECT v_archived_count, v_retry_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Process retry queue (run daily)
CREATE OR REPLACE FUNCTION process_retry_queue()
RETURNS TABLE(
  retries_ready INTEGER
) AS $$
DECLARE
  v_ready_count INTEGER := 0;
BEGIN
  -- Insert into retry_queue for archived leads whose retry_date has arrived
  WITH retries_to_schedule AS (
    INSERT INTO retry_queue (
      archived_lead_id,
      retry_message,
      scheduled_for,
      status
    )
    SELECT
      al.id,
      'Oi ' || al.company_name || ', tentei falar com vocês há alguns dias. ' ||
      'Ainda faz sentido conversarmos sobre ' ||
      COALESCE(al.context_summary, 'automação com IA') || '?',
      al.retry_date,
      'scheduled'
    FROM archived_leads al
    WHERE al.retry_scheduled = true
      AND al.retry_date <= CURRENT_DATE
      AND al.retry_status = 'pending'
      AND NOT EXISTS (
        SELECT 1 FROM retry_queue rq
        WHERE rq.archived_lead_id = al.id
      )
    RETURNING id
  )
  SELECT COUNT(*) INTO v_ready_count FROM retries_to_schedule;

  RETURN QUERY SELECT v_ready_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Cleanup failed retries (run end-of-day)
CREATE OR REPLACE FUNCTION cleanup_failed_retries()
RETURNS TABLE(
  deleted_count INTEGER
) AS $$
DECLARE
  v_deleted_count INTEGER := 0;
BEGIN
  -- Delete archived leads where retry also failed (no response after retry)
  -- Criteria: retry sent >= 1 day ago, no response

  WITH failed_retries AS (
    SELECT al.id
    FROM archived_leads al
    INNER JOIN retry_queue rq ON rq.archived_lead_id = al.id
    WHERE rq.status = 'sent'
      AND rq.sent_at < (NOW() - INTERVAL '1 day')
      AND rq.response_received = false
  ),
  deleted_archives AS (
    DELETE FROM archived_leads
    WHERE id IN (SELECT id FROM failed_retries)
    RETURNING id
  )
  SELECT COUNT(*) INTO v_deleted_count FROM deleted_archives;

  RETURN QUERY SELECT v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CRON JOBS (Requires pg_cron extension)
-- ============================================================================

-- NOTE: Uncomment and configure after installing pg_cron extension
-- Reference: https://supabase.com/docs/guides/database/extensions/pg_cron

/*
-- Run every day at 23:00 (11 PM)
SELECT cron.schedule(
  'archive-non-responders-daily',
  '0 23 * * *',
  $$SELECT archive_non_responders();$$
);

-- Run every day at 08:00 (8 AM) - prepare retry queue
SELECT cron.schedule(
  'process-retry-queue-daily',
  '0 8 * * *',
  $$SELECT process_retry_queue();$$
);

-- Run every day at 23:30 (11:30 PM) - cleanup after retry failed
SELECT cron.schedule(
  'cleanup-failed-retries-daily',
  '30 23 * * *',
  $$SELECT cleanup_failed_retries();$$
);
*/

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE leads IS 'Lead Hunter: Captured leads from Google Maps';
COMMENT ON TABLE lead_context IS 'Lead Hunter: Website context and intelligence';
COMMENT ON TABLE messages IS 'Lead Hunter: WhatsApp messages sent to leads';
COMMENT ON TABLE lead_responses IS 'Lead Hunter: Responses received from leads';
COMMENT ON TABLE message_queue IS 'Lead Hunter: Message scheduling queue (9h-17h)';
COMMENT ON TABLE archived_leads IS 'Lead Hunter: Non-responders archived for retry after 3 business days';
COMMENT ON TABLE retry_queue IS 'Lead Hunter: Second attempt messages (retry after 3 business days)';

COMMENT ON FUNCTION archive_non_responders() IS 'End-of-day: Archive non-responders, schedule retry +3 business days';
COMMENT ON FUNCTION process_retry_queue() IS 'Daily 8AM: Process retry queue for leads ready for second attempt';
COMMENT ON FUNCTION cleanup_failed_retries() IS 'End-of-day: Delete archived leads where retry also failed';
COMMENT ON FUNCTION add_business_days(DATE, INTEGER) IS 'Calculate date + N business days (skip weekends)';
