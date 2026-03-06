"""Network endpoints: /network, /network/forks."""

from fastapi import APIRouter, Depends
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
