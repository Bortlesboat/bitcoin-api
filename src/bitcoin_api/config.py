"""Application settings from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bitcoin Core RPC
    bitcoin_rpc_host: str = "127.0.0.1"
    bitcoin_rpc_port: int = 8332
    bitcoin_rpc_user: str | None = None
    bitcoin_rpc_password: str | None = None
    bitcoin_datadir: str | None = None

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 9332
    api_db_path: Path = Path("data/bitcoin_api.db")

    # CORS (comma-separated origins, or "*" for all)
    cors_origins: str = "*"

    # Rate limits (requests per minute)
    rate_limit_anonymous: int = 30
    rate_limit_free: int = 100
    rate_limit_pro: int = 500
    rate_limit_enterprise: int = 2000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
