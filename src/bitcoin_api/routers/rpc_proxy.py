"""JSON-RPC proxy: lets bitcoin-mcp route tool calls through the hosted API."""

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from bitcoinlib_rpc import BitcoinRPC

from ..dependencies import get_rpc

log = logging.getLogger(__name__)

router = APIRouter(tags=["RPC Proxy"])

# Read-only methods safe to expose. Wallet/admin methods are blocked.
ALLOWED_METHODS: set[str] = {
    # Blockchain
    "getblockchaininfo",
    "getblockcount",
    "getbestblockhash",
    "getblockhash",
    "getblock",
    "getblockheader",
    "getblockstats",
    "getchaintips",
    "getchaintxstats",
    "getdifficulty",
    # Mempool
    "getmempoolinfo",
    "getrawmempool",
    "getmempoolentry",
    "getmempoolancestors",
    "getmempooldescendants",
    # Transactions
    "getrawtransaction",
    "decoderawtransaction",
    "decodescript",
    "gettxout",
    "gettxoutproof",
    "verifytxoutproof",
    # Fee estimation
    "estimatesmartfee",
    # Mining (read-only)
    "getmininginfo",
    "getnetworkhashps",
    # Network (read-only)
    "getnetworkinfo",
    "getpeerinfo",
    "getconnectioncount",
    "getnodeaddresses",
    # UTXO
    "gettxoutsetinfo",
    # Validation
    "validateaddress",
    # Help
    "help",
    # Broadcast (the one write operation we allow)
    "sendrawtransaction",
}


@router.post("/rpc")
async def rpc_proxy(request: Request, rpc: BitcoinRPC = Depends(get_rpc)):
    """Proxy JSON-RPC calls to the Bitcoin node.

    Accepts standard JSON-RPC 2.0 requests. Only whitelisted read-only
    methods are allowed. Used by bitcoin-mcp for zero-config hosted mode.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    method = body.get("method", "")
    params = body.get("params", [])
    req_id = body.get("id", 1)

    # Store RPC method name for middleware usage logging
    request.state.rpc_method = method

    if method not in ALLOWED_METHODS:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not allowed. "
                    f"Allowed: {', '.join(sorted(ALLOWED_METHODS))}",
                },
            },
            status_code=403,
        )

    try:
        # BitcoinRPC uses __getattr__ to proxy any method name
        rpc_method = getattr(rpc, method)
        if isinstance(params, list):
            result = rpc_method(*params)
        elif isinstance(params, dict):
            result = rpc_method(**params)
        else:
            result = rpc_method()

        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    except Exception as e:
        log.warning("RPC proxy error for %s: %s", method, e)
        # Extract RPC error code if available
        code = getattr(e, "code", -32603)
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": code, "message": str(e)},
            },
            status_code=500,
        )
