"""Interactive API guide — teaches developers the entire API from their terminal."""

from enum import Enum

from fastapi import APIRouter, Query

from ..config import settings
from ..models import envelope

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
                _ep("GET", "/api/v1/fees/3", "Fee estimate for a specific block target"),
                _ep("GET", "/api/v1/fees/landscape", "Full fee landscape across all targets"),
                _ep("POST", "/api/v1/fees/estimate-tx", "Estimate fee for a specific transaction", auth=True),
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
                _ep("POST", "/api/v1/broadcast", "Broadcast a signed transaction", auth=True),
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
            "description": "Mining stats, difficulty, and next block prediction",
            "endpoints": [
                _ep("GET", "/api/v1/mining", "Mining overview: difficulty, hashrate, retarget"),
                _ep("GET", "/api/v1/mining/nextblock", "Next block fee prediction"),
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
            "description": "Server-Sent Events for live block and fee updates",
            "endpoints": [
                _ep("GET", "/api/v1/stream/blocks", "Live new block notifications (SSE)"),
                _ep("GET", "/api/v1/stream/fees", "Live fee estimate updates (SSE)"),
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
                _ep("GET", "/api/v1/address/{addr}", "Address summary"),
                _ep("GET", "/api/v1/address/{addr}/utxos", "Address UTXOs"),
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

    return cats


def _build_auth_info() -> dict:
    return {
        "method": "X-API-Key header",
        "register": "POST /api/v1/register",
        "tiers": {
            "anonymous": {
                "per_minute": settings.rate_limit_anonymous,
                "daily": 1000,
            },
            "free": {
                "per_minute": settings.rate_limit_free,
                "daily": 10000,
            },
            "pro": {
                "per_minute": settings.rate_limit_pro,
                "daily": 100000,
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

    data = {
        "welcome": "Satoshi API — Bitcoin data for developers. 55+ endpoints, zero vendor lock-in.",
        "quickstart": quickstart,
        "categories": categories,
        "auth": _build_auth_info(),
        "links": {
            "docs": "/docs",
            "register": "/api/v1/register",
            "terms": "/terms",
            "privacy": "/privacy",
            "github": "https://github.com/Bortlesboat/bitcoin-api",
        },
    }

    return envelope(data)
