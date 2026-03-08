from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from bitcoinlib_rpc import BitcoinRPC

from ..auth import require_api_key, cap_blocks_param, BLOCKS_CAP
from ..dependencies import get_rpc
from ..cache import cached_blockchain_info, cached_utxo_set_info
from ..models import ApiResponse, envelope, rpc_envelope
from ..services.stats import classify_outputs, parse_op_returns

router = APIRouter(prefix="/stats", tags=["Statistics"])

_UTXO_SET_EXAMPLE = {
    200: {
        "description": "UTXO set summary",
        "content": {"application/json": {"example": {
            "data": {
                "height": 880000,
                "txouts": 180000000,
                "total_amount_btc": 19687500.0,
                "hash": "abc123...",
                "disk_size_bytes": 12000000000,
                "bogosize": 13500000000,
            },
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_SEGWIT_ADOPTION_EXAMPLE = {
    200: {
        "description": "Output type distribution",
        "content": {"application/json": {"example": {
            "data": {
                "blocks_analyzed": 100,
                "total_outputs": 45000,
                "type_distribution": {"P2WPKH": 22000, "P2TR": 12000, "P2SH": 6000, "P2PKH": 3000, "OP_RETURN": 2000},
                "segwit_percentage": 75.56,
                "taproot_percentage": 26.67,
            },
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}

_OP_RETURNS_EXAMPLE = {
    200: {
        "description": "OP_RETURN usage statistics",
        "content": {"application/json": {"example": {
            "data": {
                "blocks_analyzed": 100,
                "total_op_returns": 2500,
                "total_bytes": 75000,
                "avg_per_block": 25.0,
                "avg_size_bytes": 30.0,
                "samples": [{"txid": "abc123...", "hex": "6a0b68656c6c6f", "size_bytes": 7}],
            },
            "meta": {"timestamp": "2026-03-07T12:00:00+00:00", "node_height": 880000, "chain": "main"},
        }}},
    }
}


@router.get("/utxo-set", response_model=ApiResponse[dict], responses=_UTXO_SET_EXAMPLE)
def utxo_set(request: Request, rpc: BitcoinRPC = Depends(get_rpc)):
    """UTXO set summary from gettxoutsetinfo. Note: this RPC call can be slow."""
    require_api_key(request, "UTXO set info")
    utxo_info = cached_utxo_set_info(rpc)
    data = {
        "height": utxo_info.get("height"),
        "txouts": utxo_info.get("txouts"),
        "total_amount_btc": utxo_info.get("total_amount"),
        "hash": utxo_info.get("hash_serialized_2") or utxo_info.get("bestblock"),
        "disk_size_bytes": utxo_info.get("disk_size"),
        "bogosize": utxo_info.get("bogosize"),
    }
    return rpc_envelope(data, rpc)


@router.get("/segwit-adoption", response_model=ApiResponse[dict], responses=_SEGWIT_ADOPTION_EXAMPLE)
def segwit_adoption(
    request: Request,
    blocks: int = Query(100, ge=1, le=1000, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Output type distribution (SegWit, Taproot, legacy) across recent blocks."""
    tier = require_api_key(request, "SegWit adoption stats")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    current_hash = info["bestblockhash"]

    total_counts: dict[str, int] = {}
    analyzed = 0

    for _ in range(blocks):
        block = rpc.call("getblock", current_hash, 2)
        counts = classify_outputs(block)
        for label, count in counts.items():
            total_counts[label] = total_counts.get(label, 0) + count
        analyzed += 1
        current_hash = block.get("previousblockhash")
        if not current_hash:
            break

    total_outputs = sum(total_counts.values())
    segwit_types = {"P2WPKH", "P2WSH", "P2TR"}
    segwit_count = sum(total_counts.get(t, 0) for t in segwit_types)
    taproot_count = total_counts.get("P2TR", 0)

    data = {
        "blocks_analyzed": analyzed,
        "total_outputs": total_outputs,
        "type_distribution": {k: v for k, v in sorted(total_counts.items(), key=lambda x: -x[1])},
        "segwit_percentage": round(segwit_count / total_outputs * 100, 2) if total_outputs else 0,
        "taproot_percentage": round(taproot_count / total_outputs * 100, 2) if total_outputs else 0,
    }
    resp = envelope(data, height=info["blocks"], chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp


@router.get("/op-returns", response_model=ApiResponse[dict], responses=_OP_RETURNS_EXAMPLE)
def op_return_stats(
    request: Request,
    blocks: int = Query(100, ge=1, le=1000, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """OP_RETURN usage statistics across recent blocks."""
    tier = require_api_key(request, "OP_RETURN stats")
    blocks = cap_blocks_param(blocks, tier)
    info = cached_blockchain_info(rpc)
    current_hash = info["bestblockhash"]

    all_op_returns = []
    analyzed = 0

    for _ in range(blocks):
        block = rpc.call("getblock", current_hash, 2)
        op_returns = parse_op_returns(block)
        all_op_returns.extend(op_returns)
        analyzed += 1
        current_hash = block.get("previousblockhash")
        if not current_hash:
            break

    total_bytes = sum(op.get("size_bytes", 0) for op in all_op_returns)

    data = {
        "blocks_analyzed": analyzed,
        "total_op_returns": len(all_op_returns),
        "total_bytes": total_bytes,
        "avg_per_block": round(len(all_op_returns) / analyzed, 2) if analyzed else 0,
        "avg_size_bytes": round(total_bytes / len(all_op_returns), 1) if all_op_returns else 0,
        "samples": all_op_returns[:10],
    }
    resp = envelope(data, height=info["blocks"], chain=info["chain"])
    resp["meta"]["max_blocks"] = BLOCKS_CAP.get(tier, 144)
    return resp
