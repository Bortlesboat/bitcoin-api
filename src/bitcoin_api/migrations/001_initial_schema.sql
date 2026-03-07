-- Initial schema: api_keys, usage_log, fee_history

CREATE TABLE IF NOT EXISTS api_keys (
    key_hash   TEXT PRIMARY KEY,
    prefix     TEXT NOT NULL,
    tier       TEXT NOT NULL DEFAULT 'free',
    label      TEXT,
    email      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash        TEXT,
    endpoint        TEXT NOT NULL,
    status          INTEGER NOT NULL,
    method          TEXT,
    response_time_ms REAL,
    user_agent      TEXT,
    ts              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage_log(ts);
CREATE INDEX IF NOT EXISTS idx_usage_key ON usage_log(key_hash);
CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage_log(key_hash, ts);
CREATE INDEX IF NOT EXISTS idx_usage_endpoint ON usage_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_usage_status ON usage_log(status);

CREATE TABLE IF NOT EXISTS fee_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL DEFAULT (datetime('now')),
    next_block_fee  REAL,
    median_fee      REAL,
    low_fee         REAL,
    mempool_size    INTEGER,
    mempool_vsize   INTEGER,
    congestion      TEXT
);

CREATE INDEX IF NOT EXISTS idx_fee_history_ts ON fee_history(ts);
