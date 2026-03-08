"""Shared response models — envelope, errors, metadata."""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    timestamp: str
    request_id: str | None = None
    node_height: int | None = None
    chain: str | None = None
    syncing: bool = False
    cached: bool = False
    cache_age_seconds: int | None = None
    max_blocks: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta


class ErrorDetail(BaseModel):
    type: str = "about:blank"
    status: int
    title: str
    detail: str
    request_id: str | None = None
    help_url: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Typed data models ---


class HealthData(BaseModel):
    status: str
    chain: str
    blocks: int


class NetworkData(BaseModel):
    version: int | None = None
    subversion: str | None = None
    protocol_version: int | None = None
    connections: int
    connections_in: int
    connections_out: int
    relay_fee: float
    incremental_fee: float
    networks: list[dict]


class FeeEstimateData(BaseModel):
    conf_target: int
    fee_rate_btc_kvb: float
    fee_rate_sat_vb: float
    errors: list[str] = []


class FeeRecommendationData(BaseModel):
    recommendation: str
    estimates: dict[int, float]


class MiningData(BaseModel):
    blocks: int
    difficulty: float
    networkhashps: float
    chain: str
    next_retarget_height: int
    blocks_until_retarget: int


class NextBlockTx(BaseModel):
    txid: str
    fee_rate: float
    fee_sats: int


class UtxoNotFoundData(BaseModel):
    in_utxo_set: bool
    txid: str
    vout: int
    note: str


class ChainTip(BaseModel):
    height: int
    hash: str
    branchlen: int
    status: str


class DecodedTransaction(BaseModel):
    txid: str
    hash: str | None = None
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    vin: list[dict]
    vout: list[dict]


class BlockAnalysisData(BaseModel):
    hash: str
    height: int
    tx_count: int
    size: int
    weight: int
    median_fee_rate: float | None = None
    total_fee: float | None = None
    top_fee_txids: list[dict] = []


class TransactionAnalysisData(BaseModel):
    txid: str
    version: int | None = None
    size: int | None = None
    vsize: int | None = None
    weight: int | None = None
    fee_sats: int | None = None
    fee_rate_sat_vb: float | None = None
    is_segwit: bool | None = None
    is_taproot: bool | None = None
    has_inscription: bool | None = None
    input_count: int | None = None
    output_count: int | None = None

    model_config = {"extra": "ignore"}


class MempoolAnalysisData(BaseModel):
    size: int
    bytes: int | None = None
    congestion: str | None = None
    next_block_min_fee: float | None = None
    fee_buckets: list[dict] = []

    model_config = {"extra": "ignore"}


class NextBlockData(BaseModel):
    height: int | None = None
    tx_count: int | None = None
    total_fees_btc: float | None = None
    total_weight: int | None = None
    min_fee_rate: float | None = None
    max_fee_rate: float | None = None
    median_fee_rate: float | None = None
    top_5: list[dict] = []

    model_config = {"extra": "ignore"}


class BroadcastRequest(BaseModel):
    hex: str = Field(max_length=2_000_000)


class BroadcastData(BaseModel):
    txid: str


class DecodeRequest(BaseModel):
    hex: str = Field(max_length=2_000_000)


# --- Helper functions ---


def build_meta(
    *, height: int | None = None, chain: str | None = None, request_id: str | None = None,
) -> Meta:
    from .cache import get_sync_progress, get_cache_state

    progress = get_sync_progress()
    syncing = progress is not None and progress < 0.9999

    is_cached, cache_age = get_cache_state()

    return Meta(
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        node_height=height,
        chain=chain,
        syncing=syncing,
        cached=is_cached,
        cache_age_seconds=cache_age,
    )


def envelope(
    data: Any,
    *,
    height: int | None = None,
    chain: str | None = None,
    request_id: str | None = None,
) -> dict:
    return ApiResponse(
        data=data,
        meta=build_meta(height=height, chain=chain, request_id=request_id),
    ).model_dump()


def rpc_envelope(data: Any, rpc) -> dict:
    """Fetch blockchain info and wrap data in standard envelope."""
    from .cache import cached_blockchain_info
    info = cached_blockchain_info(rpc)
    return envelope(data, height=info["blocks"], chain=info["chain"])
