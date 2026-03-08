"""Pydantic response models for indexed endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class IndexedAddressBalance(BaseModel):
    """Balance and statistics for an indexed address."""
    address: str
    total_received: int
    total_sent: int
    balance: int
    tx_count: int
    first_seen_height: int | None = None
    last_seen_height: int | None = None


class IndexedTransactionSummary(BaseModel):
    """Summary of a transaction in address history."""
    txid: str
    block_height: int
    tx_index: int
    value_change: int  # net satoshis (positive = received, negative = sent)
    fee: int | None = None
    timestamp: int | None = None


class IndexedAddressHistory(BaseModel):
    """Paginated transaction history for an address."""
    address: str
    transactions: list[IndexedTransactionSummary]
    total: int
    offset: int
    limit: int


class IndexedTxInput(BaseModel):
    """Transaction input from the index."""
    prev_txid: str
    prev_vout: int
    address: str | None = None
    value: int | None = None


class IndexedTxOutput(BaseModel):
    """Transaction output from the index."""
    vout: int
    value: int
    address: str | None = None
    script_type: str | None = None
    spent: bool = False


class IndexedTransactionDetail(BaseModel):
    """Enriched transaction from the index."""
    txid: str
    block_height: int
    block_hash: str
    tx_index: int
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    fee: int | None = None
    is_coinbase: bool
    input_count: int
    output_count: int
    inputs: list[IndexedTxInput]
    outputs: list[IndexedTxOutput]


class IndexerStatus(BaseModel):
    """Current indexer sync status."""
    enabled: bool
    syncing: bool
    indexed_height: int
    node_height: int | None = None
    progress_pct: float
    blocks_per_sec: float | None = None
    estimated_completion: str | None = None
    started_at: str | None = None
    last_block_at: str | None = None
