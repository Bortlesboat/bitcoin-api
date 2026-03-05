"""Status endpoints: /health, /status, /network."""

from fastapi import APIRouter, Depends

from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.status import get_status

from ..dependencies import get_rpc
from ..models import envelope

router = APIRouter(tags=["Status"])


@router.get("/health")
def health(rpc: BitcoinRPC = Depends(get_rpc)):
    """Ping the node. No auth required."""
    info = rpc.call("getblockchaininfo")
    return {"status": "ok", "chain": info["chain"], "blocks": info["blocks"]}


@router.get("/status")
def status(rpc: BitcoinRPC = Depends(get_rpc)):
    """Full node status with sync progress, peers, disk usage."""
    node = get_status(rpc)
    info = rpc.call("getblockchaininfo")
    return envelope(node.model_dump(), height=info["blocks"], chain=info["chain"])


@router.get("/network")
def network(rpc: BitcoinRPC = Depends(get_rpc)):
    """Network info: version, subversion, connections, relay fee."""
    net = rpc.call("getnetworkinfo")
    info = rpc.call("getblockchaininfo")
    data = {
        "version": net["version"],
        "subversion": net["subversion"],
        "protocol_version": net["protocolversion"],
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
