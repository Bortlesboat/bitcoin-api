-- Migration: Add client_type tracking to usage_log
ALTER TABLE usage_log ADD COLUMN client_type TEXT DEFAULT 'unknown';
ALTER TABLE usage_log ADD COLUMN referrer TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_usage_log_client_type ON usage_log(client_type);
