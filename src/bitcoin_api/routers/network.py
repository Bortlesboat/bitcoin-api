"""Network endpoints: /network/forks."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC

from ..cache import cached_blockchain_info
from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(prefix="/network", tags=["Network"])

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


@router.get("/forks", responses=_FORKS_EXAMPLE)
def chain_forks(rpc: BitcoinRPC = Depends(get_rpc)):
    """Chain tips from getchaintips — shows active chain and any forks/orphans."""
    tips = rpc.call("getchaintips")
    info = cached_blockchain_info(rpc)
    return envelope(tips, height=info["blocks"], chain=info["chain"])
