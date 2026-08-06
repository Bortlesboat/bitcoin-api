-- Block confirmation stats with feerate percentiles for research
CREATE TABLE IF NOT EXISTS block_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_height INTEGER NOT NULL UNIQUE,
    block_hash TEXT NOT NULL,
    block_time TEXT NOT NULL,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    tx_count INTEGER NOT NULL,
    total_fees_sat INTEGER NOT NULL,
    min_feerate REAL NOT NULL,
    max_feerate REAL NOT NULL,
    p10_feerate REAL NOT NULL,
    p25_feerate REAL NOT NULL,
    p50_feerate REAL NOT NULL,
    p75_feerate REAL NOT NULL,
    p90_feerate REAL NOT NULL,
    core_est_1 REAL,
    core_est_6 REAL,
    core_est_144 REAL,
    mempool_local_est REAL,
    mempool_space_est REAL
);
CREATE INDEX IF NOT EXISTS idx_bc_height ON block_confirmations(block_height);
CREATE INDEX IF NOT EXISTS idx_bc_time ON block_confirmations(block_time);

-- Multi-source fee estimate log
CREATE TABLE IF NOT EXISTS fee_estimates_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL,
    target INTEGER NOT NULL,
    feerate REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fel_ts ON fee_estimates_log(ts);
CREATE INDEX IF NOT EXISTS idx_fel_source_target ON fee_estimates_log(source, target);
