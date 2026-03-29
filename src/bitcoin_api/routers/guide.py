"""Interactive API guide — teaches developers the entire API from their terminal."""

from enum import Enum

from fastapi import APIRouter, Query

from ..config import settings
from ..models import envelope
from ..rate_limit import DAILY_LIMITS

router = APIRouter(tags=["Guide"])

_BASE = "https://bitcoinsapi.com"


class UseCaseFilter(str, Enum):
    fees = "fees"
    blocks = "blocks"
    transactions = "transactions"
    mempool = "mempool"
    mining = "mining"
    network = "network"
    streams = "streams"
    prices = "prices"
    address = "address"
    tools = "tools"
    status = "status"
    authentication = "authentication"
    supply = "supply"
    statistics = "statistics"
    billing = "billing"
    websocket = "websocket"
    admin = "admin"
    history = "history"
    all = "all"


class LangFilter(str, Enum):
    curl = "curl"
    python = "python"
    javascript = "javascript"
    all = "all"


def _ex(path: str, method: str = "GET", body: str | None = None) -> dict:
    """Build examples dict for all three languages."""
    url = f"{_BASE}{path}"
    curl = f"curl {url}" if method == "GET" else f"curl -X {method} {url}"
    py = f'requests.get("{url}")' if method == "GET" else f'requests.post("{url}"'
    js = f'fetch("{url}")' if method == "GET" else f'fetch("{url}", {{method: "{method}"'

    if body:
        curl += f" -H 'Content-Type: application/json' -d '{body}'"
        py += f", json={body})"
        js += f", headers: {{\"Content-Type\": \"application/json\"}}, body: JSON.stringify({body})}})"
    elif method != "GET":
        py += ")"
        js += "})"

    return {"curl": curl, "python": py, "javascript": js}


def _filter_examples(examples: dict, lang: str) -> dict:
    if lang == "all":
        return examples
    return {lang: examples[lang]} if lang in examples else {}


def _build_quickstart() -> list[dict]:
    return [
        {
            "step": 1,
            "action": "Check API health",
            "method": "GET",
            "path": "/api/v1/health",
            "examples": _ex("/api/v1/health"),
        },
        {
            "step": 2,
            "action": "Get a free API key (optional)",
            "method": "POST",
            "path": "/api/v1/register",
            "examples": _ex(
                "/api/v1/register",
                "POST",
                '{"email":"you@example.com","label":"my-app","agreed_to_terms":true}',
            ),
        },
        {
            "step": 3,
            "action": "Get current fee estimates",
            "method": "GET",
            "path": "/api/v1/fees/recommended",
            "examples": _ex("/api/v1/fees/recommended"),
        },
    ]


def _ep(method: str, path: str, description: str, auth: bool = False) -> dict:
    return {
        "method": method,
        "path": path,
        "description": description,
        "auth_required": auth,
        "examples": _ex(path, method),
    }


def _build_categories() -> list[dict]:
    """Build the full endpoint catalog. Feature-flagged categories checked at runtime."""
    cats = [
        {
            "name": "Fee Estimation",
            "use_case": "fees",
            "description": "Real-time fee estimates, historical trends, and smart recommendations",
            "endpoints": [
                _ep("GET", "/api/v1/fees", "Fee estimates for 1, 3, 6, 25, 144 block targets"),
                _ep("GET", "/api/v1/fees/recommended", "Smart fee recommendation with context"),
                _ep("GET", "/api/v1/fees/plan", "Transaction cost planner — estimate costs across urgency tiers (immediate/standard/patient/opportunistic). Supports profiles (simple_send, batch_payout, consolidation), address types, and USD currency."),
                _ep("GET", "/api/v1/fees/savings", "Fee savings simulation — compare always-send-now vs optimal timing over the last 7 days. Shows savings per tx and monthly projection."),
                _ep("GET", "/api/v1/fees/3", "Fee estimate for a specific block target"),
                _ep("GET", "/api/v1/fees/landscape", "Full fee landscape across all targets (premium on hosted API: x402 or paid tier)"),
                _ep("GET", "/api/v1/fees/estimate-tx", "Estimate fee for a specific transaction"),
                _ep("GET", "/api/v1/fees/history", "Historical fee data"),
                _ep("GET", "/api/v1/fees/mempool-blocks", "Projected mempool blocks with fee ranges"),
            ],
        },
        {
            "name": "Blocks",
            "use_case": "blocks",
            "description": "Block data, headers, transactions, and statistics",
            "endpoints": [
                _ep("GET", "/api/v1/blocks/latest", "Latest block summary"),
                _ep("GET", "/api/v1/blocks/tip/height", "Current chain tip height"),
                _ep("GET", "/api/v1/blocks/tip/hash", "Current chain tip hash"),
                _ep("GET", "/api/v1/blocks/880000", "Block by height or hash"),
                _ep("GET", "/api/v1/blocks/880000/stats", "Block statistics and analysis"),
                _ep("GET", "/api/v1/blocks/{hash}/header", "Raw block header"),
                _ep("GET", "/api/v1/blocks/{hash}/txids", "Transaction IDs in a block"),
                _ep("GET", "/api/v1/blocks/{hash}/txs", "Transactions in a block (paginated)"),
                _ep("GET", "/api/v1/blocks/{hash}/raw", "Raw block as hex string"),
            ],
        },
        {
            "name": "Transactions",
            "use_case": "transactions",
            "description": "Transaction lookup, decoding, and broadcasting",
            "endpoints": [
                _ep("GET", "/api/v1/tx/{txid}", "Transaction details"),
                _ep("GET", "/api/v1/tx/{txid}/raw", "Raw transaction data"),
                _ep("GET", "/api/v1/tx/{txid}/hex", "Transaction hex"),
                _ep("GET", "/api/v1/tx/{txid}/status", "Confirmation status"),
                _ep("GET", "/api/v1/tx/{txid}/outspends", "Which outputs are spent"),
                _ep("GET", "/api/v1/utxo/{txid}/{vout}", "UTXO lookup"),
                _ep("POST", "/api/v1/decode", "Decode a raw transaction hex", auth=True),
                _ep("GET", "/api/v1/tx/{txid}/merkle-proof", "Merkle proof for confirmed transaction"),
                _ep("POST", "/api/v1/broadcast", "Broadcast a signed transaction (API key or x402 on hosted API)", auth=True),
            ],
        },
        {
            "name": "Mempool",
            "use_case": "mempool",
            "description": "Mempool state, pending transactions, and congestion analysis",
            "endpoints": [
                _ep("GET", "/api/v1/mempool", "Mempool overview and analysis"),
                _ep("GET", "/api/v1/mempool/info", "Raw mempool statistics"),
                _ep("GET", "/api/v1/mempool/tx/{txid}", "Mempool transaction details"),
                _ep("GET", "/api/v1/mempool/txids", "All mempool transaction IDs"),
                _ep("GET", "/api/v1/mempool/recent", "Recently added mempool transactions"),
            ],
        },
        {
            "name": "Mining",
            "use_case": "mining",
            "description": "Mining stats, difficulty, hashrate history, and revenue analysis",
            "endpoints": [
                _ep("GET", "/api/v1/mining", "Mining overview: difficulty, hashrate, retarget"),
                _ep("GET", "/api/v1/mining/nextblock", "Next block fee prediction (premium on hosted API: x402 or paid tier)"),
                _ep("GET", "/api/v1/mining/hashrate/history", "Hashrate history over recent blocks", auth=True),
                _ep("GET", "/api/v1/mining/revenue", "Mining revenue breakdown", auth=True),
                _ep("GET", "/api/v1/mining/pools", "Pool identification from coinbase tags", auth=True),
                _ep("GET", "/api/v1/mining/difficulty/history", "Difficulty adjustment history"),
                _ep("GET", "/api/v1/mining/revenue/history", "Per-block revenue history", auth=True),
            ],
        },
        {
            "name": "Network",
            "use_case": "network",
            "description": "Node info, forks, difficulty history, and address validation",
            "endpoints": [
                _ep("GET", "/api/v1/network", "Network overview"),
                _ep("GET", "/api/v1/network/forks", "Active and proposed soft/hard forks"),
                _ep("GET", "/api/v1/network/difficulty", "Current difficulty with retarget estimate"),
                _ep("GET", "/api/v1/network/validate-address/{addr}", "Validate a Bitcoin address"),
            ],
        },
        {
            "name": "Real-Time Streams",
            "use_case": "streams",
            "description": "Server-Sent Events for live block, fee, and whale transaction updates",
            "endpoints": [
                _ep("GET", "/api/v1/stream/blocks", "Live new block notifications (SSE)"),
                _ep("GET", "/api/v1/stream/fees", "Live fee estimate updates (SSE)"),
                _ep("GET", "/api/v1/stream/whale-txs", "Live whale transaction alerts (SSE)"),
            ],
        },
        {
            "name": "Status & Health",
            "use_case": "status",
            "description": "API health checks and node status",
            "endpoints": [
                _ep("GET", "/api/v1/health", "Quick health check"),
                _ep("GET", "/api/v1/status", "Detailed node and API status"),
                _ep("GET", "/api/v1/health/deep", "Deep health check with component status", auth=True),
                _ep("GET", "/api/v1/x402-info", "x402 payment information and premium endpoint pricing"),
                _ep("GET", "/api/v1/x402-demo", "Sample 402 challenge flow for x402 client testing"),
            ],
        },
        {
            "name": "Authentication",
            "use_case": "authentication",
            "description": "API key registration and management",
            "endpoints": [
                _ep("POST", "/api/v1/register", "Register for a free API key"),
                _ep("POST", "/api/v1/unsubscribe", "Opt out of usage alert emails", auth=True),
            ],
        },
        {
            "name": "Billing",
            "use_case": "billing",
            "description": "Subscription management via Stripe",
            "endpoints": [
                _ep("POST", "/api/v1/billing/checkout", "Create a Stripe checkout session", auth=True),
                _ep("GET", "/api/v1/billing/status", "Check subscription status", auth=True),
                _ep("POST", "/api/v1/billing/cancel", "Cancel subscription", auth=True),
            ],
        },
        {
            "name": "WebSocket",
            "use_case": "websocket",
            "description": "Real-time pub/sub for blocks, fees, and transactions",
            "endpoints": [
                _ep("GET", "/api/v1/ws", "WebSocket connection for real-time subscriptions"),
            ],
        },
        {
            "name": "Admin & Monitoring",
            "use_case": "admin",
            "description": "Prometheus metrics and admin analytics (admin key required)",
            "endpoints": [
                _ep("GET", "/metrics", "Prometheus metrics endpoint"),
                _ep("GET", "/api/v1/analytics/overview", "Analytics overview", auth=True),
                _ep("GET", "/api/v1/analytics/requests", "Request volume analytics", auth=True),
                _ep("GET", "/api/v1/analytics/endpoints", "Per-endpoint analytics", auth=True),
                _ep("GET", "/api/v1/analytics/errors", "Error analytics", auth=True),
                _ep("GET", "/api/v1/analytics/user-agents", "User agent analytics", auth=True),
                _ep("GET", "/api/v1/analytics/latency", "Latency analytics", auth=True),
                _ep("GET", "/api/v1/analytics/keys", "API key analytics", auth=True),
                _ep("GET", "/api/v1/analytics/growth", "Growth analytics", auth=True),
                _ep("GET", "/api/v1/analytics/slow-endpoints", "Slowest endpoint analytics", auth=True),
                _ep("GET", "/api/v1/analytics/retention", "User retention analytics", auth=True),
                _ep("GET", "/api/v1/analytics/client-types", "Client type breakdown", auth=True),
                _ep("GET", "/api/v1/analytics/mcp-funnel", "MCP adoption funnel", auth=True),
                _ep("GET", "/api/v1/analytics/public", "Public social proof stats (no auth)"),
                _ep("GET", "/api/v1/analytics/referrers", "Top traffic referrers", auth=True),
                _ep("GET", "/api/v1/analytics/funnel", "Registration-to-usage conversion funnel", auth=True),
                _ep("GET", "/api/v1/analytics/users", "Full user list and details", auth=True),
            ],
        },
    ]

    # Feature-flagged categories
    flags = settings.feature_flags
    if flags.get("prices_router", False):
        cats.append({
            "name": "Prices",
            "use_case": "prices",
            "description": "Bitcoin price data",
            "endpoints": [
                _ep("GET", "/api/v1/prices", "Current Bitcoin prices"),
            ],
        })
    if flags.get("address_router", False):
        cats.append({
            "name": "Address",
            "use_case": "address",
            "description": "Address balance and UTXO lookup",
            "endpoints": [
                _ep("GET", "/api/v1/address/{addr}", "Address summary", auth=True),
                _ep("GET", "/api/v1/address/{addr}/utxos", "Address UTXOs", auth=True),
            ],
        })
    if flags.get("exchange_compare", False):
        cats.append({
            "name": "Tools",
            "use_case": "tools",
            "description": "Developer utilities and comparison tools",
            "endpoints": [
                _ep("GET", "/api/v1/tools/exchange-compare", "Compare exchange rates"),
            ],
        })
    if flags.get("supply_router", False):
        cats.append({
            "name": "Supply",
            "use_case": "supply",
            "description": "Bitcoin supply data and issuance schedule",
            "endpoints": [
                _ep("GET", "/api/v1/supply", "Current Bitcoin supply statistics"),
            ],
        })
    if flags.get("stats_router", False):
        cats.append({
            "name": "Statistics",
            "use_case": "statistics",
            "description": "On-chain statistics and adoption metrics",
            "endpoints": [
                _ep("GET", "/api/v1/stats/utxo-set", "UTXO set statistics", auth=True),
                _ep("GET", "/api/v1/stats/segwit-adoption", "SegWit adoption metrics", auth=True),
                _ep("GET", "/api/v1/stats/op-returns", "OP_RETURN data analysis", auth=True),
            ],
        })

    # History Explorer (conditional — siloed feature)
    if settings.enable_history_explorer:
        cats.append({
            "name": "History Explorer",
            "use_case": "history",
            "description": "Curated Bitcoin history timeline with on-chain exploration",
            "endpoints": [
                _ep("GET", "/api/v1/history/events", "List historical Bitcoin events (filterable by era, category, tag)"),
                _ep("GET", "/api/v1/history/events/{event_id}", "Get details for a specific historical event"),
                _ep("GET", "/api/v1/history/eras", "List all Bitcoin eras"),
                _ep("GET", "/api/v1/history/concepts", "List Bitcoin protocol concepts with try-it links"),
                _ep("GET", "/api/v1/history/search", "Search historical events by keyword"),
            ],
        })

    return cats


def _build_auth_info() -> dict:
    return {
        "method": "X-API-Key header",
        "register": "POST /api/v1/register",
        "tiers": {
            "anonymous": {
                "per_minute": settings.rate_limit_anonymous,
                "daily": DAILY_LIMITS["anonymous"],
            },
            "free": {
                "per_minute": settings.rate_limit_free,
                "daily": DAILY_LIMITS["free"],
            },
            "pro": {
                "per_minute": settings.rate_limit_pro,
                "daily": DAILY_LIMITS["pro"],
            },
            "enterprise": {
                "per_minute": settings.rate_limit_enterprise,
                "daily": "unlimited",
            },
        },
    }


@router.get("/guide")
def guide(
    use_case: UseCaseFilter = Query(UseCaseFilter.all, description="Filter by use case category"),
    lang: LangFilter = Query(LangFilter.curl, description="Code example language"),
):
    """Interactive API guide. Teaches you the entire API from your terminal."""
    categories = _build_categories()

    # Filter by use_case
    if use_case != UseCaseFilter.all:
        categories = [c for c in categories if c["use_case"] == use_case.value]

    # Filter examples by lang
    lang_val = lang.value
    if lang_val != "all":
        for cat in categories:
            for ep in cat["endpoints"]:
                ep["examples"] = _filter_examples(ep["examples"], lang_val)

    quickstart = _build_quickstart()
    if lang_val != "all":
        for step in quickstart:
            step["examples"] = _filter_examples(step["examples"], lang_val)

    total = sum(len(c["endpoints"]) for c in categories)
    data = {
        "welcome": "Satoshi API — Bitcoin fee intelligence for developers and AI agents. Zero vendor lock-in.",
        "quickstart": quickstart,
        "categories": categories,
        "auth": _build_auth_info(),
        "links": {
            "docs": "/docs",
            "register": "/api/v1/register",
            "x402": "/x402",
            "terms": "/terms",
            "privacy": "/privacy",
            "github": "https://github.com/Bortlesboat/bitcoin-api",
        },
    }

    return envelope(data)
