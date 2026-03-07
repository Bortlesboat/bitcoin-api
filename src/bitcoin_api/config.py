"""Application settings from environment variables."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bitcoin Core RPC
    bitcoin_rpc_host: str = "127.0.0.1"
    bitcoin_rpc_port: int = 8332
    bitcoin_rpc_user: str | None = None
    bitcoin_rpc_password: SecretStr | None = None
    bitcoin_datadir: str | None = None

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 9332
    api_db_path: Path = Path("data/bitcoin_api.db")

    # CORS (comma-separated origins, or "*" for all — use "*" only for local/dev)
    cors_origins: str = "http://localhost:3000,http://localhost:9332"

    # Feature flags (toggleable routers)
    enable_exchange_compare: bool = True
    enable_prices_router: bool = True
    enable_address_router: bool = True
    enable_supply_router: bool = True
    enable_stats_router: bool = True

    # Whale transaction SSE threshold
    whale_tx_threshold_btc: float = 10.0

    @property
    def feature_flags(self) -> dict[str, bool]:
        """Map of feature flag name → router module name → enabled."""
        return {
            "exchange_compare": self.enable_exchange_compare,
            "prices_router": self.enable_prices_router,
            "address_router": self.enable_address_router,
            "supply_router": self.enable_supply_router,
            "stats_router": self.enable_stats_router,
        }

    # Logging format ("text" or "json")
    log_format: str = "text"

    # RPC timeout (seconds)
    rpc_timeout: int = 30

    # Rate limits (requests per minute)
    rate_limit_anonymous: int = 30
    rate_limit_free: int = 100
    rate_limit_pro: int = 500
    rate_limit_enterprise: int = 2000

    # Admin API key for analytics endpoints
    admin_api_key: str | None = None

    # WebSocket
    ws_max_connections: int = 100

    # Stripe billing (all optional — billing disabled if stripe_secret_key is None)
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_id: str = ""
    stripe_success_url: str = "https://bitcoinsapi.com?checkout=success"
    stripe_cancel_url: str = "https://bitcoinsapi.com?checkout=cancel"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
