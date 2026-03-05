"""Shared response models — envelope, errors, metadata."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class Meta(BaseModel):
    timestamp: str
    node_height: int | None = None
    chain: str | None = None


class ApiResponse(BaseModel):
    data: Any
    meta: Meta


class ErrorDetail(BaseModel):
    status: int
    title: str
    detail: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def build_meta(*, height: int | None = None, chain: str | None = None) -> Meta:
    return Meta(
        timestamp=datetime.now(timezone.utc).isoformat(),
        node_height=height,
        chain=chain,
    )


def envelope(data: Any, *, height: int | None = None, chain: str | None = None) -> dict:
    return ApiResponse(
        data=data,
        meta=build_meta(height=height, chain=chain),
    ).model_dump()
