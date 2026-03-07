from fastapi import APIRouter, Depends, Query
from bitcoinlib_rpc import BitcoinRPC

from ..dependencies import get_rpc
from ..cache import cached_blockchain_info
from ..models import ApiResponse, envelope
from ..services.stats import classify_outputs, parse_op_returns

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/utxo-set", response_model=ApiResponse[dict])
def utxo_set(rpc: BitcoinRPC = Depends(get_rpc)):
    """UTXO set summary from gettxoutsetinfo. Note: this RPC call can be slow."""
    info = cached_blockchain_info(rpc)
    utxo_info = rpc.call("gettxoutsetinfo")
    data = {
        "height": utxo_info.get("height"),
        "txouts": utxo_info.get("txouts"),
        "total_amount_btc": utxo_info.get("total_amount"),
        "hash": utxo_info.get("hash_serialized_2") or utxo_info.get("bestblock"),
        "disk_size_bytes": utxo_info.get("disk_size"),
        "bogosize": utxo_info.get("bogosize"),
    }
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/segwit-adoption", response_model=ApiResponse[dict])
def segwit_adoption(
    blocks: int = Query(100, ge=1, le=1000, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """Output type distribution (SegWit, Taproot, legacy) across recent blocks."""
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
    return envelope(data, height=info["blocks"], chain=info["chain"])


@router.get("/op-returns", response_model=ApiResponse[dict])
def op_return_stats(
    blocks: int = Query(100, ge=1, le=1000, description="Number of blocks to analyze"),
    rpc: BitcoinRPC = Depends(get_rpc),
):
    """OP_RETURN usage statistics across recent blocks."""
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
    return envelope(data, height=info["blocks"], chain=info["chain"])
