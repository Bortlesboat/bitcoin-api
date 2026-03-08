ALTER TABLE usage_log ADD COLUMN client_ip TEXT DEFAULT '';
ALTER TABLE api_keys ADD COLUMN registration_ip TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_usage_log_client_ip ON usage_log(client_ip);
