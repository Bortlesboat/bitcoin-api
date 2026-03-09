"""Satoshi API Python SDK — typed client for bitcoinsapi.com.

Zero dependencies (stdlib only). Works with Python 3.10+.

Usage:
    from satoshi_api import SatoshiAPI

    api = SatoshiAPI()                          # anonymous (30 req/min)
    api = SatoshiAPI(api_key="your-key")        # authenticated
    api = SatoshiAPI(base_url="http://localhost:9332")  # self-hosted

    fees = api.fees()
    block = api.block(840000)
    tx = api.transaction("txid...")
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

__version__ = "0.1.0"

_DEFAULT_BASE_URL = "https://bitcoinsapi.com"
_DEFAULT_TIMEOUT = 30


@dataclass
class APIError(Exception):
    """Error returned by the Satoshi API."""
    status: int
    title: str
    detail: str
    error_type: str = "about:blank"
    request_id: str | None = None

    def __str__(self) -> str:
        return f"[{self.status}] {self.title}: {self.detail}"


@dataclass
class RateLimitError(APIError):
    """429 Too Many Requests — check retry_after for when to retry."""
    retry_after: int = 60

    def __str__(self) -> str:
        return f"[429] Rate limited. Retry after {self.retry_after}s"


@dataclass
class Response:
    """Wrapper for API responses with data + metadata."""
    data: Any
    meta: dict = field(default_factory=dict)
    _raw: dict = field(default_factory=dict, repr=False)

    @property
    def height(self) -> int | None:
        return self.meta.get("node_height")

    @property
    def chain(self) -> str | None:
        return self.meta.get("chain")

    @property
    def cached(self) -> bool:
        return self.meta.get("cached", False)

    @property
    def request_id(self) -> str | None:
        return self.meta.get("request_id")


class SatoshiAPI:
    """Python client for the Satoshi API.

    Args:
        base_url: API base URL (default: https://bitcoinsapi.com)
        api_key: Optional API key for authenticated access
        timeout: Request timeout in seconds (default: 30)
        retry_on_429: Auto-retry on rate limit with backoff (default: True)
        max_retries: Max retries on 429 (default: 3)
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        retry_on_429: bool = True,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_on_429 = retry_on_429
        self.max_retries = max_retries

    def _request(self, method: str, path: str, body: dict | None = None) -> Response:
        url = f"{self.base_url}/api/v1{path}"
        headers = {"Accept": "application/json", "User-Agent": f"satoshi-api-python/{__version__}"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        data = json.dumps(body).encode() if body else None
        if data:
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())
                    return Response(
                        data=result.get("data", result),
                        meta=result.get("meta", {}),
                        _raw=result,
                    )
            except urllib.error.HTTPError as e:
                response_body = e.read().decode()
                try:
                    err = json.loads(response_body).get("error", {})
                except (json.JSONDecodeError, AttributeError):
                    err = {}

                if e.code == 429 and self.retry_on_429 and attempt < self.max_retries:
                    retry_after = int(e.headers.get("Retry-After", 60))
                    time.sleep(retry_after)
                    continue

                if e.code == 429:
                    raise RateLimitError(
                        status=429,
                        title=err.get("title", "Rate Limited"),
                        detail=err.get("detail", "Too many requests"),
                        error_type=err.get("type", "about:blank"),
                        request_id=err.get("request_id"),
                        retry_after=int(e.headers.get("Retry-After", 60)),
                    )

                raise APIError(
                    status=e.code,
                    title=err.get("title", f"HTTP {e.code}"),
                    detail=err.get("detail", response_body[:200]),
                    error_type=err.get("type", "about:blank"),
                    request_id=err.get("request_id"),
                )
            except urllib.error.URLError as e:
                raise ConnectionError(f"Cannot reach {self.base_url}: {e.reason}") from e

        raise APIError(status=429, title="Rate Limited", detail="Max retries exceeded")

    def _get(self, path: str, **params: Any) -> Response:
        query_parts = []
        for k, v in params.items():
            if v is not None:
                query_parts.append(f"{k}={v}")
        if query_parts:
            path = f"{path}?{'&'.join(query_parts)}"
        return self._request("GET", path)

    def _post(self, path: str, body: dict) -> Response:
        return self._request("POST", path, body)

    # --- Status & Health ---

    def health(self) -> Response:
        """Node health check (chain, blocks, status)."""
        return self._get("/health")

    def health_deep(self) -> Response:
        """Deep health check (DB, jobs, caches, circuit breaker)."""
        return self._get("/health/deep")

    def status(self) -> Response:
        """Full node status (sync progress, peers, disk, version)."""
        return self._get("/status")

    # --- Blocks ---

    def block(self, height_or_hash: int | str) -> Response:
        """Get block analysis by height or hash."""
        return self._get(f"/blocks/{height_or_hash}")

    def block_latest(self) -> Response:
        """Get the latest block."""
        return self._get("/blocks/latest")

    def block_stats(self, height: int) -> Response:
        """Raw block statistics from Bitcoin Core."""
        return self._get(f"/blocks/{height}/stats")

    def block_header(self, block_hash: str) -> Response:
        """Get block header by hash."""
        return self._get(f"/blocks/{block_hash}/header")

    def block_txids(self, block_hash: str) -> Response:
        """Get transaction IDs in a block."""
        return self._get(f"/blocks/{block_hash}/txids")

    def block_txs(self, block_hash: str, start: int = 0, limit: int = 25) -> Response:
        """Get transactions in a block (paginated)."""
        return self._get(f"/blocks/{block_hash}/txs", start=start, limit=limit)

    def block_raw(self, block_hash: str) -> Response:
        """Get raw block hex by hash."""
        return self._get(f"/blocks/{block_hash}/raw")

    def tip_height(self) -> Response:
        """Current chain tip height."""
        return self._get("/blocks/tip/height")

    def tip_hash(self) -> Response:
        """Current chain tip hash."""
        return self._get("/blocks/tip/hash")

    # --- Transactions ---

    def transaction(self, txid: str) -> Response:
        """Get decoded transaction by txid."""
        return self._get(f"/tx/{txid}")

    def transaction_hex(self, txid: str) -> Response:
        """Get raw transaction hex."""
        return self._get(f"/tx/{txid}/hex")

    def transaction_raw(self, txid: str) -> Response:
        """Get raw transaction (full JSON from Bitcoin Core)."""
        return self._get(f"/tx/{txid}/raw")

    def transaction_status(self, txid: str) -> Response:
        """Check if transaction is confirmed."""
        return self._get(f"/tx/{txid}/status")

    def transaction_outspends(self, txid: str) -> Response:
        """Check spending status of each output."""
        return self._get(f"/tx/{txid}/outspends")

    def broadcast(self, hex_data: str) -> Response:
        """Broadcast a signed transaction. Requires API key."""
        return self._post("/broadcast", {"hex": hex_data})

    def decode(self, hex_data: str) -> Response:
        """Decode a raw transaction without broadcasting. Requires API key."""
        return self._post("/decode", {"hex": hex_data})

    def utxo(self, txid: str, vout: int) -> Response:
        """Check if a UTXO exists in the current set."""
        return self._get(f"/utxo/{txid}/{vout}")

    # --- Fees ---

    def fees(self) -> Response:
        """Fee estimates for multiple confirmation targets."""
        return self._get("/fees")

    def fee_target(self, target: int) -> Response:
        """Fee estimate for a specific confirmation target."""
        return self._get(f"/fees/{target}")

    def fee_recommended(self) -> Response:
        """Recommended fees (fast, medium, slow)."""
        return self._get("/fees/recommended")

    def fee_landscape(self) -> Response:
        """Complete fee analysis with trend, recommendation, and scenarios."""
        return self._get("/fees/landscape")

    def fee_mempool_blocks(self) -> Response:
        """Projected mempool blocks with fee distribution."""
        return self._get("/fees/mempool-blocks")

    def fee_estimate_tx(
        self, inputs: int = 1, outputs: int = 2,
        input_type: str = "p2wpkh", output_type: str = "p2wpkh",
    ) -> Response:
        """Estimate fee for a transaction with given input/output counts."""
        return self._get("/fees/estimate-tx", inputs=inputs, outputs=outputs,
                         input_type=input_type, output_type=output_type)

    def fee_history(self, hours: int = 24, interval: str = "10m") -> Response:
        """Historical fee rates and mempool size."""
        return self._get("/fees/history", hours=hours, interval=interval)

    def fee_plan(
        self, profile: str | None = None, inputs: int | None = None,
        outputs: int | None = None, address_type: str = "segwit",
        currency: str = "sats",
    ) -> Response:
        """Transaction cost planner — estimate costs across urgency tiers.

        Call with no params for a standard SegWit transaction, or use a profile
        preset (simple_send, exchange_withdrawal, batch_payout, consolidation).
        Set currency='usd' to include USD equivalents.
        """
        return self._get("/fees/plan", profile=profile, inputs=inputs,
                         outputs=outputs, address_type=address_type,
                         currency=currency)

    def fee_savings(self, hours: int = 168, currency: str = "sats") -> Response:
        """Fee savings simulation — how much you'd save with optimal timing.

        Compares average fee cost vs. optimal timing over the requested period.
        Set currency='usd' to include USD equivalents.
        """
        return self._get("/fees/savings", hours=hours, currency=currency)

    # --- Mempool ---

    def mempool(self) -> Response:
        """Mempool analysis (size, congestion, fee buckets)."""
        return self._get("/mempool")

    def mempool_info(self) -> Response:
        """Raw mempool info from Bitcoin Core."""
        return self._get("/mempool/info")

    def mempool_txids(self) -> Response:
        """All transaction IDs currently in the mempool."""
        return self._get("/mempool/txids")

    def mempool_recent(self) -> Response:
        """Recently added mempool transactions."""
        return self._get("/mempool/recent")

    def mempool_tx(self, txid: str) -> Response:
        """Get mempool entry for a specific transaction."""
        return self._get(f"/mempool/tx/{txid}")

    # --- Mining ---

    def mining(self) -> Response:
        """Mining info (difficulty, hashrate, next retarget)."""
        return self._get("/mining")

    def mining_nextblock(self) -> Response:
        """Next block prediction (fees, tx count, top transactions)."""
        return self._get("/mining/nextblock")

    # --- Network ---

    def network(self) -> Response:
        """Network info (connections, version, relay fee)."""
        return self._get("/network")

    def network_difficulty(self) -> Response:
        """Difficulty adjustment info."""
        return self._get("/network/difficulty")

    def network_forks(self) -> Response:
        """Chain tips and forks."""
        return self._get("/network/forks")

    def validate_address(self, address: str) -> Response:
        """Validate a Bitcoin address."""
        return self._get(f"/network/validate-address/{address}")

    # --- Address (requires txindex) ---

    def address(self, address: str) -> Response:
        """Address summary (balance, tx count)."""
        return self._get(f"/address/{address}")

    def address_utxos(self, address: str) -> Response:
        """UTXOs for an address."""
        return self._get(f"/address/{address}/utxos")

    # --- Supply ---

    def supply(self) -> Response:
        """Bitcoin supply breakdown: circulating supply, inflation rate, halving countdown."""
        return self._get("/supply")

    # --- Prices ---

    def prices(self) -> Response:
        """BTC price in multiple currencies with 24h change."""
        return self._get("/prices")

    # --- Tools ---

    def exchange_compare(self, amount_usd: float = 100) -> Response:
        """Compare exchange fees for buying BTC."""
        return self._get("/tools/exchange-compare", amount_usd=amount_usd)

    # --- Guide ---

    def guide(self, use_case: str | None = None, lang: str | None = None) -> Response:
        """Interactive API guide with examples."""
        return self._get("/guide", use_case=use_case, lang=lang)

    # --- Key Management ---

    def register(self, email: str, label: str | None = None) -> Response:
        """Register for a free API key.

        Args:
            email: Email address for the new key.
            label: Optional label for the key (max 100 chars).

        Returns:
            Response with data containing ``api_key``, ``tier``, and ``label``.
        """
        body: dict[str, Any] = {"email": email, "agreed_to_terms": True}
        if label is not None:
            body["label"] = label
        resp = self._post("/register", body)
        return resp
