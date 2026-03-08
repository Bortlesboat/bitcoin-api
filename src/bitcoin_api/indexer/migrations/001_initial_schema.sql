-- Indexer schema: blocks, transactions, inputs, outputs, address summaries

CREATE TABLE IF NOT EXISTS blocks (
    height       INTEGER PRIMARY KEY,
    hash         BYTEA NOT NULL UNIQUE,
    prev_hash    BYTEA NOT NULL,
    timestamp    INTEGER NOT NULL,
    tx_count     INTEGER NOT NULL,
    size         INTEGER NOT NULL,
    weight       INTEGER NOT NULL,
    indexed_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS block_undo (
    height    INTEGER PRIMARY KEY REFERENCES blocks(height) ON DELETE CASCADE,
    undo_data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    txid         BYTEA PRIMARY KEY,
    block_height INTEGER NOT NULL REFERENCES blocks(height) ON DELETE CASCADE,
    tx_index     SMALLINT NOT NULL,
    version      SMALLINT NOT NULL,
    size         INTEGER NOT NULL,
    vsize        INTEGER NOT NULL,
    weight       INTEGER NOT NULL,
    locktime     INTEGER NOT NULL,
    fee          BIGINT,
    is_coinbase  BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions(block_height);

CREATE TABLE IF NOT EXISTS tx_outputs (
    txid        BYTEA NOT NULL,
    vout        SMALLINT NOT NULL,
    value       BIGINT NOT NULL,
    script_type TEXT,
    address     TEXT,
    spent_txid  BYTEA,
    spent_vin   SMALLINT,
    PRIMARY KEY (txid, vout)
);
CREATE INDEX IF NOT EXISTS idx_txo_address ON tx_outputs(address) WHERE address IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_txo_unspent ON tx_outputs(address) WHERE spent_txid IS NULL AND address IS NOT NULL;

CREATE TABLE IF NOT EXISTS tx_inputs (
    txid      BYTEA NOT NULL,
    vin       SMALLINT NOT NULL,
    prev_txid BYTEA NOT NULL,
    prev_vout SMALLINT NOT NULL,
    PRIMARY KEY (txid, vin)
);
CREATE INDEX IF NOT EXISTS idx_txi_prev ON tx_inputs(prev_txid, prev_vout);

CREATE TABLE IF NOT EXISTS address_summary (
    address        TEXT PRIMARY KEY,
    total_received BIGINT NOT NULL DEFAULT 0,
    total_sent     BIGINT NOT NULL DEFAULT 0,
    tx_count       INTEGER NOT NULL DEFAULT 0,
    first_seen     INTEGER,
    last_seen      INTEGER
);

CREATE TABLE IF NOT EXISTS indexer_state (
    id           INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    tip_height   INTEGER NOT NULL DEFAULT 0,
    tip_hash     BYTEA,
    started_at   TIMESTAMPTZ,
    last_block_at TIMESTAMPTZ,
    blocks_per_sec REAL
);
INSERT INTO indexer_state (id, tip_height) VALUES (1, 0) ON CONFLICT DO NOTHING;
