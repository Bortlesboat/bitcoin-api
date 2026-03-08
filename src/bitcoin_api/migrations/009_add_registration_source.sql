-- Track where API key registrations come from (referrer + UTM params)
ALTER TABLE api_keys ADD COLUMN registration_referrer TEXT DEFAULT '';
ALTER TABLE api_keys ADD COLUMN utm_source TEXT DEFAULT '';
ALTER TABLE api_keys ADD COLUMN utm_medium TEXT DEFAULT '';
ALTER TABLE api_keys ADD COLUMN utm_campaign TEXT DEFAULT '';
