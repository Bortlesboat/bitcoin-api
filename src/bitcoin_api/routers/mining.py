"""Mining endpoints: /mining, /mining/nextblock."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info, cached_next_block
from ..dependencies import get_rpc
from ..models import ApiResponse, MiningData, envelope

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


@router.get("/nextblock", response_model=ApiResponse[dict], responses=_NEXT_BLOCK_EXAMPLE)
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
