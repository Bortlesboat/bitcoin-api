CREATE TABLE IF NOT EXISTS x402_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    endpoint TEXT NOT NULL,
    price_usd TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    pay_to TEXT,
    client_ip_hash TEXT,
    payment_id TEXT,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_x402_timestamp ON x402_payments(timestamp);
CREATE INDEX IF NOT EXISTS idx_x402_status ON x402_payments(payment_status)
