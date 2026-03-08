"""Indexer configuration — isolated from main API settings."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class IndexerSettings(BaseSettings):
    """Settings for the blockchain indexer. All env vars prefixed with INDEXER_."""

    enabled: bool = False
    postgres_dsn: str = "postgresql://satoshi:satoshi@localhost:5432/satoshi_index"
    zmq_endpoint: str = "tcp://127.0.0.1:28332"
    batch_size: int = 10
    reorg_depth: int = 100

    @field_validator("batch_size")
    @classmethod
    def batch_size_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("batch_size must be > 0")
        return v

    @field_validator("reorg_depth")
    @classmethod
    def reorg_depth_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("reorg_depth must be > 0")
        return v

    model_config = {"env_prefix": "INDEXER_"}


indexer_settings = IndexerSettings()
