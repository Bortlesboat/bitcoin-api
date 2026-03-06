"""Status endpoints: /health, /status, /network."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info, cached_status
from ..dependencies import get_rpc
from ..models import ApiResponse, HealthData, envelope

router = APIRouter(tags=["Status"])

_HEALTH_EXAMPLE = {
    200: {
        "description": "Node is reachable",
        "content": {
            "application/json": {
                "example": {
                    "data": {"status": "ok", "chain": "main", "blocks": 939462},
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

_STATUS_EXAMPLE = {
    200: {
        "description": "Full node status",
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "chain": "main",
                        "blocks": 939462,
                        "headers": 939462,
                        "best_block_hash": "00000000000000000002a7c4c1e48d76"
                        "c5a37902165a270156b7a8d72688a093",
                        "difficulty": 113757508674661.0,
                        "verification_progress": 0.9999987,
                        "size_on_disk": 654321098765,
                        "pruned": False,
                        "peers": 125,
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

@router.get("/health", response_model=ApiResponse[HealthData], responses=_HEALTH_EXAMPLE)
def health(rpc: BitcoinRPC = Depends(get_rpc)):
    """Ping the node. No auth required."""
    info = cached_blockchain_info(rpc)
    return envelope(
        {"status": "ok", "chain": info["chain"], "blocks": info["blocks"]},
        height=info["blocks"],
        chain=info["chain"],
    )


@router.get("/status", response_model=ApiResponse[dict], responses=_STATUS_EXAMPLE)
def status(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full node status with sync progress, peers, disk usage."""
    node = cached_status(rpc)
    info = cached_blockchain_info(rpc)
    return envelope(node.model_dump(), height=info["blocks"], chain=info["chain"])


