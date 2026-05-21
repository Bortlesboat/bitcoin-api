"""Status endpoints: /health, /status, /network, /x402-demo."""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

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
            "positioning": "Bitcoin fee intelligence that saves you money on every transaction.",
            "firstCall": {
                "endpoint": "/api/v1/fees/landscape",
                "buyer_value": "Compare fee choices before broadcasting so you can save money on every transaction.",
                "why_first": "Lowest-risk paid evaluation: the response should make the fee tradeoff obvious before repeat use.",
            },
            "measurement": {
                "onboarding_variant": "fee-savings-first-call",
                "safe_to_log": [
                    "endpoint_pattern",
                    "status_bucket",
                    "client_type_bucket",
                    "onboarding_variant",
                ],
                "do_not_log": [
                    "raw IPs",
                    "raw user agents",
                    "payment proofs",
                    "wallet material",
                    "private keys",
                    "signatures",
                ],
            },
            "paidEndpoints": endpoints,
            "freeEndpoints": "All endpoints not listed above are free -- no payment required.",
            "howItWorks": {
                "1": "Requesting a paid endpoint without payment returns a 402 challenge with paymentRequirements.",
                "2": "Inspect the value, price, and endpoint pattern before deciding whether your own x402 client should pay.",
                "3": "Only send payment material from a trusted wallet/client that you control.",
            },
            "tryIt": "curl https://bitcoinsapi.com/api/v1/x402-demo",
            "demo": "https://bitcoinsapi.com/api/v1/x402-demo",
            "docs": "https://x402.org/docs",
            "sdk": "https://github.com/coinbase/x402",
        }
    except ImportError:
        return {
            "x402": False,
            "message": "x402 payments are not enabled on this instance.",
        }


@router.get("/x402-demo")
def x402_demo(x_payment: str | None = Header(None)):
    """x402 demo/sandbox endpoint. Returns a sample 402 response so developers can test their x402 client integration.

    - Without X-PAYMENT header: returns 402 with sample payment requirements
    - With X-PAYMENT header (any value): returns 200 with success message

    This is NOT a real payment — no funds are transferred. Use this to
    understand the x402 flow before hitting real paid endpoints.
    """
    if x_payment:
        # Simulate successful payment flow without accepting or verifying real payment material.
        return {
            "data": {
                "message": "x402 demo: demo header observed; no payment was processed.",
                "flow": "demo_complete",
                "explanation": (
                    "This sandbox only confirms that your client can attach a demo header. "
                    "No funds are transferred and no payment proof is verified here. "
                    "Evaluate value first with /api/v1/fees/landscape before any real paid call."
                ),
                "recommended_first_paid_endpoint": "/api/v1/fees/landscape",
                "agent_guidance": "Do not attach a real payment to this demo endpoint; use a controlled x402 client only after evaluating value and price.",
                "safe_measurement": {
                    "stage": "demo_complete",
                    "variant": "demo-no-payment-safe",
                    "endpoint_pattern": "/api/v1/x402-demo",
                },
                "next_steps": [
                    "Inspect paymentRequirements on a 402 challenge before paying.",
                    "Compare expected fee savings with the endpoint price.",
                    "See all paid endpoints: GET /api/v1/x402-info",
                ],
            },
            "meta": {"demo": True, "x402_flow": "demo_header_observed"},
        }

    # No payment header — return 402 with sample requirements
    return JSONResponse(
        status_code=402,
        content={
            "error": "Payment Required",
            "x402_demo": True,
            "message": (
                "This is a DEMO 402 response. In production, paid endpoints return this format. "
                "Do not attach a real payment to this demo endpoint; use it only to inspect challenge shape."
            ),
            "onboarding_variant": "demo-no-payment-safe",
            "recommended_first_paid_endpoint": "/api/v1/fees/landscape",
            "agent_guidance": (
                "Do not attach a real payment to this demo endpoint. "
                "If you later use a real paid endpoint, first compare expected savings with the listed price."
            ),
            "safe_measurement": {
                "stage": "challenge",
                "variant": "demo-no-payment-safe",
                "endpoint_pattern": "/api/v1/x402-demo",
            },
            "paymentRequirements": {
                "scheme": "exact",
                "network": "eip155:8453",
                "maxAmountRequired": "0",
                "resource": "https://bitcoinsapi.com/api/v1/x402-demo",
                "description": "x402 demo — no real payment needed",
                "mimeType": "application/json",
                "payTo": "0x0000000000000000000000000000000000000000",
                "maxTimeoutSeconds": 300,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "extra": {
                    "name": "USDC",
                    "chain": "Base",
                    "note": "This is a demo. No real payment is required.",
                },
            },
            "how_to_pay": {
                "1": "Parse the paymentRequirements from this 402 response",
                "2": "Confirm maxAmountRequired is zero for this demo challenge",
                "3": "Do not attach wallet material or a real payment to the demo endpoint",
                "4": "For real paid endpoints, use your own trusted x402 client only after evaluating price and value",
            },
            "try_it": "curl https://bitcoinsapi.com/api/v1/x402-demo",
            "docs": "https://x402.org/docs",
            "sdk": "https://github.com/coinbase/x402",
        },
    )
