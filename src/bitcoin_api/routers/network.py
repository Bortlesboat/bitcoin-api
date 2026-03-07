"""Network endpoints: /network, /network/forks, /network/difficulty, /validate-address/{address}."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path
from starlette.requests import Request

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import ApiResponse, NetworkData, envelope

router = APIRouter(prefix="/network", tags=["Network"])

_NETWORK_EXAMPLE = {
    200: {
        "description": "Network info",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "version": 280100,
                        "subversion": "/Satoshi:28.1.0/",
                        "protocol_version": 70016,
                        "connections": 125,
                        "connections_in": 87,
                        "connections_out": 38,
                        "relay_fee": 0.00001,
                        "incremental_fee": 0.00001,
                        "networks": [
                            {"name": "ipv4", "reachable": True},
                            {"name": "ipv6", "reachable": True},
                            {"name": "onion", "reachable": True},
                            {"name": "i2p", "reachable": False},
                            {"name": "cjdns", "reachable": False},
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

_FORKS_EXAMPLE = {
    200: {
        "description": "Chain tips showing active chain and any forks",
        "content": {
            "application/json": {
                "example": {
                    "data": [
                        {
                            "height": 939462,
                            "hash": "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a68cd",
                            "branchlen": 0,
                            "status": "active",
                        },
                        {
                            "height": 939460,
                            "hash": "000000000000000000034f1a23b8e1fa9e5f5bc91cfe1b2c8c5a2b3d4e5f6a7b",
                            "branchlen": 1,
                            "status": "valid-fork",
                        },
                    ],
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


@router.get("", response_model=ApiResponse[NetworkData], responses=_NETWORK_EXAMPLE)
def network(request: Request, rpc: BitcoinRPC = Depends(get_rpc)):
    """Network info: version, subversion, connections, relay fee."""
    net = rpc.call("getnetworkinfo")
    info = cached_blockchain_info(rpc)
    tier = getattr(request.state, "tier", "anonymous")
    data = {
        "version": None if tier == "anonymous" else net["version"],
        "subversion": None if tier == "anonymous" else net["subversion"],
        "protocol_version": None if tier == "anonymous" else net["protocolversion"],
        "connections": net["connections"],
        "connections_in": net.get("connections_in", 0),
        "connections_out": net.get("connections_out", 0),
        "relay_fee": net["relayfee"],
        "incremental_fee": net["incrementalfee"],
        "networks": [
            {"name": n["name"], "reachable": n["reachable"]}
            for n in net.get("networks", [])
        ],
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/forks", response_model=ApiResponse[list[dict]], responses=_FORKS_EXAMPLE)
def chain_forks(rpc: BitcoinRPC = Depends(get_rpc)):
    """Chain tips from getchaintips — shows active chain and any forks/orphans."""
    tips = rpc.call("getchaintips")
    info = cached_blockchain_info(rpc)
    return envelope(tips, height=info["blocks"], chain=info["chain"])


_DIFFICULTY_EXAMPLE = {
    200: {
        "description": "Current difficulty adjustment progress and estimate",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "difficulty": 119126831040958.3,
                        "current_epoch_start_height": 881280,
                        "blocks_in_epoch": 1954,
                        "blocks_remaining": 62,
                        "progress_percent": 96.9,
                        "estimated_retarget_date": "2026-03-08T14:00:00+00:00",
                        "previous_retarget_percent": 3.2,
                    },
                    "meta": {"node_height": 883234, "chain": "main"},
                }
            }
        },
    }
}


@router.get("/difficulty", response_model=ApiResponse[dict], responses=_DIFFICULTY_EXAMPLE)
def difficulty_adjustment(rpc: BitcoinRPC = Depends(get_rpc)):
    """Current difficulty epoch progress, estimated adjustment, and retarget timing."""
    info = cached_blockchain_info(rpc)
    height = info["blocks"]
    difficulty = info["difficulty"]

    # Difficulty adjusts every 2016 blocks
    epoch_start = (height // 2016) * 2016
    blocks_in_epoch = height - epoch_start
    blocks_remaining = 2016 - blocks_in_epoch
    progress = round(blocks_in_epoch / 2016 * 100, 1)

    # Estimate retarget date: blocks_remaining * 10 min avg block time
    estimated_seconds_remaining = blocks_remaining * 600
    estimated_retarget_ts = int(time.time()) + estimated_seconds_remaining
    estimated_retarget = datetime.fromtimestamp(estimated_retarget_ts, tz=timezone.utc).isoformat()

    data = {
        "difficulty": difficulty,
        "current_epoch_start_height": epoch_start,
        "blocks_in_epoch": blocks_in_epoch,
        "blocks_remaining": blocks_remaining,
        "progress_percent": progress,
        "estimated_retarget_date": estimated_retarget,
    }
    return envelope(data, height=height, chain=info["chain"])


_VALIDATE_EXAMPLE = {
    200: {
        "description": "Address validation result",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "isvalid": True,
                        "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                        "scriptPubKey": "0014751e76e8199196d454941c45d1b3a323f1433bd6",
                        "isscript": False,
                        "iswitness": True,
                        "witness_version": 0,
                    },
                    "meta": {"node_height": 881234, "chain": "main"},
                }
            }
        },
    }
}


@router.get(
    "/validate-address/{address}",
    response_model=ApiResponse[dict],
    responses=_VALIDATE_EXAMPLE,
    tags=["Network"],
)
def validate_address(
    address: str = Path(description="Bitcoin address to validate"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Validate a Bitcoin address and return its properties."""
    result = rpc.call("validateaddress", address)
    info = cached_blockchain_info(rpc)
    return envelope(result, height=info["blocks"], chain=info["chain"])
