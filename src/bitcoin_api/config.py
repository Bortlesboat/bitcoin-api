"""Application settings from environment variables."""

from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bitcoin Core RPC
    bitcoin_rpc_host: str = "127.0.0.1"
    bitcoin_rpc_port: int = 8332
    bitcoin_rpc_user: str | None = None
    bitcoin_rpc_password: SecretStr | None = None
    bitcoin_datadir: str | None = None

    # Fallback Bitcoin RPC (optional — used when primary node is down)
    bitcoin_rpc_fallback_host: str | None = None
    bitcoin_rpc_fallback_port: int = 8332
    bitcoin_rpc_fallback_user: str | None = None
    bitcoin_rpc_fallback_password: SecretStr | None = None

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
            "psbt_router": self.enable_psbt_router,
        }

    # Logging format ("text" or "json")
    log_format: str = "text"

    # RPC timeout (seconds)
    rpc_timeout: int = 30

    # Request timeout (seconds) — cancels slow requests to prevent queue buildup
    request_timeout: int = 15

    # Rate limits (requests per minute)
    rate_limit_anonymous: int = 30
    rate_limit_free: int = 100
    rate_limit_pro: int = 500
    rate_limit_enterprise: int = 2000

    # Admin API key for analytics endpoints
    admin_api_key: SecretStr | None = None

    # WebSocket
    ws_max_connections: int = 100

    # Stripe billing (all optional — billing disabled if stripe_secret_key is None)
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_id: str = ""
    stripe_success_url: str = "https://bitcoinsapi.com?checkout=success"
    stripe_cancel_url: str = "https://bitcoinsapi.com?checkout=cancel"

    # Resend (transactional email)
    resend_api_key: SecretStr | None = None
    resend_from_email: str = "Satoshi API <noreply@bitcoinsapi.com>"
    resend_enabled: bool = False
    admin_notification_email: str = ""  # ADMIN_NOTIFICATION_EMAIL — new-registration alerts

    # Upstash Redis (rate limiting backend)
    upstash_redis_url: str = ""
    upstash_redis_token: SecretStr | None = None
    rate_limit_backend: str = "memory"  # "redis" or "memory"

    # PostHog Analytics (privacy-first: no autocapture, no session recording)
    posthog_api_key: SecretStr | None = None
    posthog_host: str = "https://us.i.posthog.com"
    posthog_enabled: bool = False

    # History Explorer (siloed — curated Bitcoin history + on-chain exploration UI)
    enable_history_explorer: bool = True

    # PSBT security analysis (siloed — no node required, pure parsing)
    enable_psbt_router: bool = False

    # Fee Observatory (siloed — reads observatory.db read-only)
    enable_observatory: bool = True
    observatory_db_path: str = "~/.bitcoin-fee-observatory/observatory.db"

    # Blockchain indexer (siloed — see indexer/config.py for indexer-specific settings)
    enable_indexer: bool = False

    # AI features (all optional — AI endpoints return 503 if no provider configured)
    enable_ai_features: bool = False
    # Azure OpenAI (priority 1)
    azure_openai_endpoint: str | None = None
    azure_openai_key: SecretStr | None = None
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-10-21"
    # OpenAI direct (priority 2)
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    # Ollama (priority 3 — local fallback)
    ollama_url: str | None = None  # e.g. http://192.168.1.238:11434
    ollama_model: str = "qwen2.5:14b"
    # AI rate limit (requests per minute, separate from API key rate limits)
    ai_rate_limit: int = 10

    # MCP internal API key for loopback calls (avoids anonymous rate limits)
    mcp_internal_api_key: str = ""

    # OpenTelemetry (vendor-neutral observability)
    otel_service_name: str = "satoshi-api"
    applicationinsights_connection_string: str | None = None

    @model_validator(mode="after")
    def _validate_db_path(self):
        db_str = str(self.api_db_path)
        if ".." in db_str:
            raise ValueError("api_db_path must not contain '..' (path traversal)")
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
