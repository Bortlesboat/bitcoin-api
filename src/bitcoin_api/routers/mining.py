"""Mining endpoints: /mining, /mining/nextblock, hashrate history, revenue, pools, difficulty."""

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from bitcoinlib_rpc import BitcoinRPC

from ..auth import require_api_key, cap_blocks_param, BLOCKS_CAP
from ..cache import cached_blockchain_info, cached_next_block
from ..dependencies import get_rpc
from ..models import ApiResponse, MiningData, NextBlockData, envelope
from ..services.mining import parse_coinbase_tag, extract_coinbase_hex, calculate_hashrate

router = APIRouter(prefix="/mining", tags=["Mining"])

_MINING_SUMMARY_EXAMPLE = {
    200: {
        "description": "Mining summary with hashrate, difficulty, and retarget info",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "blocks": 939462,
                        "difficulty": 113757508517790.0,
                        "networkhashps": 8.12e20,
                        "chain": "main",
                        "next_retarget_height": 940032,
                        "blocks_until_retarget": 570,
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}

_NEXT_BLOCK_EXAMPLE = {
    200: {
        "description": "Block template analysis — what the next block would look like",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "tx_count": 3842,
                        "total_fees_btc": 0.18432,
                        "total_weight": 3992820,
                        "min_fee_rate": 5.01,
                        "max_fee_rate": 312.5,
                        "median_fee_rate": 14.2,
                        "top_5": [
                            {"txid": "a1b2c3d4e5f6...0001", "fee_rate": 312.5, "fee_sats": 48000},
                            {"txid": "b2c3d4e5f6a1...0002", "fee_rate": 285.0, "fee_sats": 42750},
                            {"txid": "c3d4e5f6a1b2...0003", "fee_rate": 248.3, "fee_sats": 37245},
                            {"txid": "d4e5f6a1b2c3...0004", "fee_rate": 210.0, "fee_sats": 31500},
                            {"txid": "e5f6a1b2c3d4...0005", "fee_rate": 195.7, "fee_sats": 29355},
                        ],
                    },
                    "meta": {
                        "timestamp": "2026-03-05T12:00:00+00:00",
                        "node_height": 939462,
                        "chain": "main",
                    },
                }
            }
        },
    }
}

_HASHRATE_HISTORY_EXAMPLE = {
    200: {
        "description": "Hashrate derived from block difficulty",
        "content": {"application/json": {"example": {
            "data": [
                {"height": 879998, "timestamp": 1709654200, "hashrate_eh_s": 786.32, "difficulty": 110000000000000.0},
                {"height": 879999, "timestamp": 1709654400, "hashrate_eh_s": 786.32, "difficulty": 110000000000000.0},
            ],
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_MINING_REVENUE_EXAMPLE = {
    200: {
        "description": "Mining revenue breakdown",
        "content": {"application/json": {"example": {
            "data": {
                "blocks_analyzed": 144,
                "total_subsidy_btc": 450.0,
                "total_fees_btc": 3.6,
                "total_revenue_btc": 453.6,
                "avg_revenue_per_block_btc": 3.15,
                "fee_percentage": 0.79,
            },
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_MINING_POOLS_EXAMPLE = {
    200: {
        "description": "Pool identification from coinbase tags",
        "content": {"application/json": {"example": {
            "data": {
                "blocks_analyzed": 144,
                "pools": [
                    {"name": "foundry", "blocks_found": 42, "percentage": 29.17},
                    {"name": "antpool", "blocks_found": 28, "percentage": 19.44},
                    {"name": "f2pool", "blocks_found": 18, "percentage": 12.5},
                ],
                "unknown_count": 12,
                "unknown_percentage": 8.33,
            },
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_DIFFICULTY_HISTORY_EXAMPLE = {
    200: {
        "description": "Difficulty at epoch boundaries",
        "content": {"application/json": {"example": {
            "data": [
                {"epoch": 434, "height": 875232, "difficulty": 95672678345126.0, "timestamp": 1708000000},
                {"epoch": 435, "height": 877248, "difficulty": 110000000000000.0, "timestamp": 1709200000, "change_pct": 14.96},
            ],
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_REVENUE_HISTORY_EXAMPLE = {
    200: {
        "description": "Per-block mining revenue",
        "content": {"application/json": {"example": {
            "data": [
                {"height": 879999, "subsidy_btc": 3.125, "fees_btc": 0.025, "total_btc": 3.15, "tx_count": 3500},
                {"height": 880000, "subsidy_btc": 3.125, "fees_btc": 0.031, "total_btc": 3.156, "tx_count": 3200},
            ],
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}


@router.get("", response_model=ApiResponse[MiningData], responses=_MINING_SUMMARY_EXAMPLE)
def mining_summary(rpc: BitcoinRPC = Depends(get_rpc)):
    """Mining summary: hashrate, difficulty, next retarget estimate."""
    info = cached_blockchain_info(rpc)
    mining = rpc.call("getmininginfo")
    data = {
        "blocks": mining["blocks"],
        "difficulty": mining["difficulty"],
        "networkhashps": mining.get("networkhashps", 0),
        "chain": mining["chain"],
        "next_retarget_height": ((mining["blocks"] // 2016) + 1) * 2016,
        "blocks_until_retarget": ((mining["blocks"] // 2016) + 1) * 2016 - mining["blocks"],
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/nextblock", response_model=ApiResponse[NextBlockData], responses=_NEXT_BLOCK_EXAMPLE)
def next_block(rpc: BitcoinRPC = Depends(get_rpc)):
    """Analyze the current block template — what the next block would look like if mined now."""
    data = dict(cached_next_block(rpc))
    info = cached_blockchain_info(rpc)
    # Convert top_5 tuples to dicts for JSON
    if data.get("top_5"):
        data["top_5"] = [
            {"txid": t[0], "fee_rate": round(t[1], 2), "fee_sats": t[2]}
            for t in data["top_5"]
        ]
    # Remove raw fee_rates list (too large for API response)
    data.pop("fee_rates", None)
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/hashrate/history", response_model=ApiResponse[list], responses=_HASHRATE_HISTORY_EXAMPLE)
def hashrate_history(
    request: Request,
    blocks: int = Query(144, ge=1, le=2016, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Hashrate history derived from difficulty over recent blocks."""
    tier = getattr(request.state, "tier", "anonymous")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    current_hash = info["bestblockhash"]

    results = []
    for _ in range(blocks):
        header = rpc.call("getblockheader", current_hash, True)
        hr = calculate_hashrate(header["difficulty"])
        results.append({
            "height": header["height"],
            "timestamp": header["time"],
            "hashrate_eh_s": round(hr / 1e18, 2),
            "difficulty": header["difficulty"],
        })
        current_hash = header.get("previousblockhash")
        if not current_hash:
            break

    results.reverse()
    resp = envelope(results, height=info["blocks"], chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp


@router.get("/revenue", response_model=ApiResponse[dict], responses=_MINING_REVENUE_EXAMPLE)
def mining_revenue(
    request: Request,
    blocks: int = Query(144, ge=1, le=2016, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Mining revenue breakdown: subsidy vs fees over recent blocks."""
    tier = require_api_key(request, "mining revenue")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    tip = info["blocks"]

    total_subsidy = 0
    total_fees = 0
    count = min(blocks, tip)

    for h in range(tip, tip - count, -1):
        stats = rpc.call("getblockstats", h)
        total_subsidy += stats.get("subsidy", 0)
        total_fees += stats.get("totalfee", 0)

    total_subsidy_btc = total_subsidy / 1e8
    total_fees_btc = total_fees / 1e8
    total_rev = total_subsidy_btc + total_fees_btc

    data = {
        "blocks_analyzed": count,
        "total_subsidy_btc": round(total_subsidy_btc, 8),
        "total_fees_btc": round(total_fees_btc, 8),
        "total_revenue_btc": round(total_rev, 8),
        "avg_revenue_per_block_btc": round(total_rev / count, 8) if count else 0,
        "fee_percentage": round(total_fees_btc / total_rev * 100, 2) if total_rev else 0,
    }
    resp = envelope(data, height=tip, chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp


@router.get("/pools", response_model=ApiResponse[dict], responses=_MINING_POOLS_EXAMPLE)
def mining_pools(
    request: Request,
    blocks: int = Query(144, ge=1, le=2016, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Identify mining pools from coinbase tags over recent blocks."""
    tier = require_api_key(request, "mining pools")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    current_hash = info["bestblockhash"]

    pool_counts: dict[str, int] = {}
    analyzed = 0

    for _ in range(blocks):
        block = rpc.call("getblock", current_hash, 2)
        coinbase_hex = extract_coinbase_hex(block)
        pool = parse_coinbase_tag(coinbase_hex)
        pool_counts[pool] = pool_counts.get(pool, 0) + 1
        analyzed += 1
        current_hash = block.get("previousblockhash")
        if not current_hash:
            break

    pools = sorted(
        [{"name": name, "blocks_found": count, "percentage": round(count / analyzed * 100, 2)}
         for name, count in pool_counts.items() if name != "Unknown"],
        key=lambda x: x["blocks_found"],
        reverse=True,
    )
    unknown = pool_counts.get("Unknown", 0)

    data = {
        "blocks_analyzed": analyzed,
        "pools": pools,
        "unknown_count": unknown,
        "unknown_percentage": round(unknown / analyzed * 100, 2) if analyzed else 0,
    }
    resp = envelope(data, height=info["blocks"], chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp


@router.get("/difficulty/history", response_model=ApiResponse[list], responses=_DIFFICULTY_HISTORY_EXAMPLE)
def difficulty_history(
    epochs: int = Query(10, ge=1, le=50, description="Number of difficulty epochs"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Difficulty adjustment history at epoch boundaries."""
    info = cached_blockchain_info(rpc)
    tip = info["blocks"]
    current_epoch_start = (tip // 2016) * 2016

    results = []
    for i in range(epochs):
        epoch_height = current_epoch_start - (i * 2016)
        if epoch_height < 0:
            break
        block_hash = rpc.call("getblockhash", epoch_height)
        header = rpc.call("getblockheader", block_hash, True)

        entry = {
            "epoch": epoch_height // 2016,
            "height": epoch_height,
            "difficulty": header["difficulty"],
            "timestamp": header["time"],
        }
        results.append(entry)

    results.reverse()
    # Calculate change_pct comparing each epoch to the previous
    for i in range(1, len(results)):
        prev_diff = results[i - 1]["difficulty"]
        if prev_diff:
            results[i]["change_pct"] = round(
                (results[i]["difficulty"] - prev_diff) / prev_diff * 100, 2
            )

    return envelope(results, height=tip, chain=info["chain"])


@router.get("/revenue/history", response_model=ApiResponse[list], responses=_REVENUE_HISTORY_EXAMPLE)
def revenue_history(
    request: Request,
    blocks: int = Query(144, ge=1, le=2016, description="Number of blocks"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Per-block mining revenue history (subsidy + fees)."""
    tier = require_api_key(request, "mining revenue history")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    tip = info["blocks"]
    count = min(blocks, tip)

    results = []
    for h in range(tip - count + 1, tip + 1):
        stats = rpc.call("getblockstats", h)
        results.append({
            "height": h,
            "subsidy_btc": round(stats.get("subsidy", 0) / 1e8, 8),
            "fees_btc": round(stats.get("totalfee", 0) / 1e8, 8),
            "total_btc": round((stats.get("subsidy", 0) + stats.get("totalfee", 0)) / 1e8, 8),
            "tx_count": stats.get("txs", 0),
        })

    resp = envelope(results, height=tip, chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp
