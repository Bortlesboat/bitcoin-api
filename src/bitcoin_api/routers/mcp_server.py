"""Hosted MCP endpoint — serve MCP protocol over SSE at /mcp.

Lets any MCP client connect with just a URL, zero install:

    {
        "mcpServers": {
            "satoshi-api": {
                "url": "https://bitcoinsapi.com/mcp/sse"
            }
        }
    }
"""

import logging
import os
import re

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from .. import __version__

log = logging.getLogger("bitcoin_api.mcp")

API_BASE = "http://127.0.0.1:9332/api/v1"
_TXID_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")

# Internal API key for loopback calls — avoids anonymous rate limits.
# Set MCP_INTERNAL_API_KEY in .env to a valid key; without it, anonymous limits apply.
_INTERNAL_KEY = os.environ.get("MCP_INTERNAL_API_KEY", "")

# Shared httpx client — avoids creating a new TCP connection per request.
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=API_BASE, timeout=15.0)
    return _client


def _internal_headers() -> dict:
    """Return headers for loopback API calls, including the internal key if set."""
    if _INTERNAL_KEY:
        return {"X-API-Key": _INTERNAL_KEY}
    return {}


async def _api_get(path: str, params: dict | None = None, timeout: float = 30) -> dict:
    """Call the local Satoshi API and return the JSON response."""
    client = _get_client()
    resp = await client.get(path, params=params, headers=_internal_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


async def _api_post(path: str, json_body: dict, api_key: str | None = None,
                    timeout: float = 30) -> dict:
    """POST to the local Satoshi API."""
    headers = _internal_headers()
    if api_key:
        headers["X-API-Key"] = api_key
    client = _get_client()
    resp = await client.post(path, json=json_body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _extract_data(result: dict) -> dict:
    """Unwrap the Satoshi API envelope, returning just the data payload."""
    return result.get("data", result)


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Satoshi API",
    instructions=(
        "Bitcoin fee intelligence API. Provides real-time fee estimates, "
        "mempool analysis, block data, mining stats, and supply info. "
        "Use get_situation_summary for a quick overview, get_fee_recommendation "
        "to decide whether to send now or wait, and search to look up any "
        "Bitcoin identifier (txid, block hash, address, height)."
    ),
)


# ---------------------------------------------------------------------------
# Core Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_api_info() -> dict:
    """Get Satoshi API version, capabilities, and endpoint count. Self-describing metadata."""
    return {
        "name": "Satoshi API",
        "version": __version__,
        "description": "Bitcoin fee intelligence that saves money on every transaction",
        "endpoints": 82,
        "tools_exposed": 17,
        "website": "https://bitcoinsapi.com",
        "docs": "https://bitcoinsapi.com/docs",
        "source": "https://github.com/Bortlesboat/bitcoin-api",
    }


@mcp.tool()
async def get_situation_summary() -> dict:
    """Get a complete Bitcoin situation summary in one call: block height, fee rates,
    mempool congestion, and fee recommendation. This is the best starting point for
    understanding what's happening on the Bitcoin network right now."""
    health = _extract_data(await _api_get("/health"))
    fees_raw = await _api_get("/fees/landscape")
    fees = _extract_data(fees_raw)
    mempool_raw = await _api_get("/mempool")
    mempool = _extract_data(mempool_raw)

    return {
        "height": health.get("blocks"),
        "chain": health.get("chain"),
        "fee_recommendation": fees.get("recommendation"),
        "fee_reasoning": fees.get("reasoning"),
        "fee_environment": fees.get("fee_environment", {}).get("level"),
        "next_block_fee_sat_vb": fees.get("current_fees", {}).get("next_block"),
        "six_block_fee_sat_vb": fees.get("current_fees", {}).get("six_blocks"),
        "one_day_fee_sat_vb": fees.get("current_fees", {}).get("one_day"),
        "mempool_tx_count": mempool.get("size"),
        "mempool_bytes": mempool.get("bytes"),
        "mempool_congestion": mempool.get("congestion"),
        "trend": fees.get("trend", {}).get("direction"),
    }


@mcp.tool()
async def get_fee_recommendation() -> dict:
    """Should I send a Bitcoin transaction now or wait? Returns a clear recommendation
    (send/wait/urgent_only) with confidence level, reasoning, fee environment
    classification, and mempool trend analysis."""
    result = await _api_get("/fees/landscape")
    return _extract_data(result)


@mcp.tool()
async def get_fee_estimates() -> dict:
    """Get raw fee rate estimates at standard confirmation targets (1, 3, 6, 25, 144 blocks).
    Returns fee rates in both BTC/kvB and sat/vB."""
    result = await _api_get("/fees")
    return _extract_data(result)


@mcp.tool()
async def estimate_transaction_cost(
    inputs: int = 1,
    outputs: int = 2,
    input_type: str = "p2wpkh",
    output_type: str = "p2wpkh",
) -> dict:
    """Estimate the cost of a Bitcoin transaction in sats and BTC at different
    confirmation targets. Specify the number of inputs/outputs and script types
    (p2pkh, p2wpkh, p2sh, p2wsh, p2tr) to get accurate size and fee estimates."""
    result = await _api_get("/fees/estimate-tx", params={
        "inputs": inputs, "outputs": outputs,
        "input_type": input_type, "output_type": output_type,
    })
    return _extract_data(result)


@mcp.tool()
async def get_mempool_status() -> dict:
    """Get current mempool status: transaction count, size in bytes, congestion level,
    fee buckets breakdown, and next-block minimum fee rate."""
    result = await _api_get("/mempool")
    return _extract_data(result)


@mcp.tool()
async def get_latest_block() -> dict:
    """Get the most recently mined block: height, hash, timestamp, transaction count,
    size, weight, median fee rate, and total fees."""
    result = await _api_get("/blocks/latest")
    return _extract_data(result)


@mcp.tool()
async def get_block(height_or_hash: str) -> dict:
    """Get a specific block by height (integer) or block hash (64-char hex string).
    Returns block analysis including tx count, size, weight, fee stats."""
    result = await _api_get(f"/blocks/{height_or_hash}")
    return _extract_data(result)


@mcp.tool()
async def get_transaction(txid: str) -> dict:
    """Decode and analyze a Bitcoin transaction by its txid (64-char hex).
    Returns size, vsize, weight, fee, fee rate, SegWit/Taproot flags,
    inscription detection, input/output counts."""
    if not _TXID_RE.match(txid):
        return {"error": "Invalid txid: must be 64 hex characters"}
    result = await _api_get(f"/tx/{txid}")
    return _extract_data(result)


@mcp.tool()
async def get_address_balance(address: str, api_key: str = "") -> dict:
    """Get the confirmed balance of a Bitcoin address (UTXO-based scan).
    Requires an API key. Returns balance in BTC and sats, UTXO count,
    and address type. Supports legacy, SegWit, and Taproot addresses."""
    if not api_key:
        return {"error": "API key required for address lookups. Register free: POST https://bitcoinsapi.com/api/v1/register"}
    try:
        client = _get_client()
        headers = _internal_headers()
        headers["X-API-Key"] = api_key  # user's key takes precedence
        resp = await client.get(
            f"/address/{address}",
            headers=headers,
            timeout=90,
        )
        resp.raise_for_status()
        return _extract_data(resp.json())
    except httpx.HTTPStatusError as e:
        return {"error": f"Address lookup failed: {e.response.status_code}", "detail": e.response.text}


@mcp.tool()
async def plan_transaction(
    profile: str = "simple_send",
    inputs: int | None = None,
    outputs: int | None = None,
    address_type: str = "segwit",
    currency: str = "sats",
) -> dict:
    """Transaction cost planner -- the most actionable tool for sending Bitcoin.
    Returns costs at 4 urgency tiers (immediate/standard/patient/opportunistic),
    delay savings percentage, trend analysis, and historical fee comparison.
    Profiles: simple_send, exchange_withdrawal, batch_payout, consolidation.
    Set currency='usd' for USD equivalents."""
    params = {"address_type": address_type, "currency": currency}
    if profile:
        params["profile"] = profile
    if inputs is not None:
        params["inputs"] = inputs
    if outputs is not None:
        params["outputs"] = outputs
    result = await _api_get("/fees/plan", params=params)
    return _extract_data(result)


@mcp.tool()
async def broadcast_transaction(raw_tx_hex: str, api_key: str = "") -> dict:
    """Broadcast a signed raw transaction to the Bitcoin network.
    Requires an API key (register free at POST /api/v1/register).
    The raw_tx_hex parameter is the fully signed transaction in hex format."""
    if not api_key:
        return {"error": "API key required. Register free: POST https://bitcoinsapi.com/api/v1/register"}
    if not _HEX_RE.match(raw_tx_hex):
        return {"error": "Invalid hex string"}
    try:
        result = await _api_post("/broadcast", {"hex": raw_tx_hex}, api_key=api_key)
        return _extract_data(result)
    except httpx.HTTPStatusError as e:
        return {"error": f"Broadcast failed: {e.response.status_code}", "detail": e.response.text}


# ---------------------------------------------------------------------------
# Intelligence Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_fee_landscape() -> dict:
    """Comprehensive fee analysis: recommendation, confidence, trend direction,
    mempool change percentage, current fee rates at multiple targets,
    and cost scenarios (send now vs wait 1hr vs wait 1 day) with savings percentages."""
    result = await _api_get("/fees/landscape")
    return _extract_data(result)


@mcp.tool()
async def get_mining_info() -> dict:
    """Bitcoin mining summary: current hashrate, difficulty, block height,
    next difficulty retarget height, and blocks until retarget."""
    result = await _api_get("/mining")
    return _extract_data(result)


@mcp.tool()
async def get_network_info() -> dict:
    """Bitcoin network status: peer connections (in/out), relay fee,
    reachable networks (IPv4, IPv6, Tor, I2P, CJDNS)."""
    result = await _api_get("/network")
    return _extract_data(result)


@mcp.tool()
async def get_supply_info() -> dict:
    """Bitcoin supply data: circulating supply, percent mined, current block subsidy,
    halvings completed, next halving height, blocks until halving,
    and annual inflation rate."""
    result = await _api_get("/supply")
    return _extract_data(result)


@mcp.tool()
async def search(query: str) -> dict:
    """Smart search: paste any Bitcoin identifier and get the right result.
    Accepts a txid (64 hex chars), block hash (64 hex chars starting with 0s),
    block height (integer), or Bitcoin address (bc1.../1.../3...).
    Automatically detects the type and returns the appropriate data."""
    q = query.strip()

    # Block height
    if q.isdigit():
        result = await _api_get(f"/blocks/{q}")
        return {"type": "block", "data": _extract_data(result)}

    # Txid or block hash (64 hex chars)
    if _TXID_RE.match(q):
        # Block hashes typically start with many zeros
        if q.startswith("00000000"):
            try:
                result = await _api_get(f"/blocks/{q}")
                return {"type": "block", "data": _extract_data(result)}
            except httpx.HTTPStatusError:
                pass
        # Try as transaction
        try:
            result = await _api_get(f"/tx/{q}")
            return {"type": "transaction", "data": _extract_data(result)}
        except httpx.HTTPStatusError:
            # Maybe it was a block hash after all
            try:
                result = await _api_get(f"/blocks/{q}")
                return {"type": "block", "data": _extract_data(result)}
            except httpx.HTTPStatusError:
                return {"error": f"Not found as transaction or block: {q[:16]}..."}

    # Bitcoin address
    if q.startswith(("bc1", "1", "3", "tb1", "m", "n", "2")):
        result = await _api_get(f"/network/validate-address/{q}")
        return {"type": "address", "data": _extract_data(result)}

    return {"error": f"Could not identify input type for: {q[:32]}"}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_mcp_app() -> Starlette:
    """Create and return the MCP SSE Starlette app for mounting."""
    log.info("Creating MCP server with %d tools", len(mcp._tool_manager._tools))
    app = mcp.sse_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    return app
