"""Shared response models — envelope, errors, metadata."""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    timestamp: str
    request_id: str | None = None
    node_height: int | None = None
    chain: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: Meta


class ErrorDetail(BaseModel):
    status: int
    title: str
    detail: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Typed data models ---


class HealthData(BaseModel):
    status: str
    chain: str
    blocks: int


class NetworkData(BaseModel):
    version: int
    subversion: str
    protocol_version: int
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


class DecodeRequest(BaseModel):
    hex: str


# --- Helper functions ---


def build_meta(
    *, height: int | None = None, chain: str | None = None, request_id: str | None = None,
) -> Meta:
    return Meta(
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        node_height=height,
        chain=chain,
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
