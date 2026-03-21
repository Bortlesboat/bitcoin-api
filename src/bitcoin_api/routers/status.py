"""Status endpoints: /health, /status, /network."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info, cached_status
from ..dependencies import get_rpc
from ..models import ApiResponse, HealthData, envelope, rpc_envelope

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
    return rpc_envelope(node.model_dump(), rpc)


@router.get("/x402-info")
def x402_info():
    """x402 payment information. Shows which endpoints accept micropayments and how to pay."""
    try:
        from bitcoin_api_x402.pricing import ENDPOINT_PRICES
        from ..config import settings as _settings
        endpoints = [
            {
                "pattern": ep.pattern,
                "price_usd": ep.price_usd,
                "description": ep.description,
            }
            for ep in ENDPOINT_PRICES
        ]
        return {
            "x402": _settings.enable_x402,
            "protocol": "https://x402.org",
            "version": 1,
            "scheme": "exact",
            "network": "eip155:8453",
            "payTo": _settings.x402_pay_to_address,
            "facilitatorUrl": "https://x402.org/facilitator",
            "paidEndpoints": endpoints,
            "freeEndpoints": "All endpoints not listed above are free -- no payment required.",
            "howItWorks": {
                "1": "Request a paid endpoint without payment -> get 402 with paymentRequirements",
                "2": "Sign a USDC payment on Base and resend with X-PAYMENT header",
                "3": "Payment is verified and you get the response",
            },
            "tryIt": "curl https://bitcoinsapi.com/api/v1/ai/explain-tx/test123",
            "docs": "https://x402.org/docs",
            "sdk": "https://github.com/coinbase/x402",
        }
    except ImportError:
        return {
            "x402": False,
            "message": "x402 payments are not enabled on this instance.",
        }


