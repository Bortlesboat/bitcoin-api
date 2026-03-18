"""AI-powered endpoints: explain transactions, blocks, fee advice, and Bitcoin Q&A.

All endpoints require ENABLE_AI_FEATURES=true and a configured AI provider
(Azure OpenAI, OpenAI, or Ollama). Returns 503 when AI is not configured.
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.transactions import analyze_transaction

from ..auth import require_api_key
from ..cache import cached_blockchain_info, cached_fee_estimates, cached_raw_mempool, get_mempool_snapshots
from ..dependencies import get_rpc
from ..models import envelope, rpc_envelope
from ..services.ai import (
    AINotConfiguredError,
    SYSTEM_PROMPT_BLOCK,
    SYSTEM_PROMPT_CHAT,
    SYSTEM_PROMPT_FEE_ADVICE,
    SYSTEM_PROMPT_TX,
    get_ai_provider,
)
from ..services.fees import calculate_fee_landscape
from ..services.price import get_cached_price
from ..validators import validate_txid

log = logging.getLogger("bitcoin_api.routers.ai")

router = APIRouter(prefix="/ai", tags=["AI"])


async def _ai_complete(system_prompt: str, user_content: str, *, max_tokens: int = 1024) -> str:
    """Call the AI provider, handling errors consistently."""
    provider = get_ai_provider()
    try:
        return await provider.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
        )
    except AINotConfiguredError:
        raise HTTPException(status_code=503, detail="AI features are temporarily unavailable.")
    except Exception:
        log.exception("AI provider error")
        raise HTTPException(status_code=502, detail="AI provider temporarily unavailable. Please try again later.")


@router.get(
    "/explain/transaction/{txid}",
    responses={
        200: {
            "description": "Plain English transaction explanation",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
                            "explanation": "This transaction consolidated 5 UTXOs into 1 output, paying 2,400 sats in fees (8 sat/vB). The fee was reasonable — current median is 12 sat/vB.",
                            "provider": "azure_openai",
                        },
                        "meta": {"timestamp": "2026-03-15T12:00:00+00:00"},
                    }
                }
            },
        }
    },
)
async def explain_transaction(
    txid: str = Path(description="Transaction ID (hex)"),
    rpc: BitcoinRPC = Depends(get_rpc),
    _tier: str = Depends(require_api_key),
):
    """Plain English explanation of a Bitcoin transaction."""
    validate_txid(txid)
    analysis = analyze_transaction(rpc, txid)
    tx_data = analysis.model_dump()

    # Build context for the AI
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in cached_fee_estimates(rpc)}
    current_next_block = fee_dict.get(1, 0)

    context = json.dumps({
        "txid": txid,
        "size": tx_data.get("size"),
        "vsize": tx_data.get("vsize"),
        "weight": tx_data.get("weight"),
        "fee_sat": tx_data.get("fee_sat"),
        "fee_rate_sat_vb": tx_data.get("fee_rate_sat_vb"),
        "is_segwit": tx_data.get("is_segwit"),
        "is_taproot": tx_data.get("is_taproot"),
        "has_inscription": tx_data.get("has_inscription"),
        "input_count": tx_data.get("input_count"),
        "output_count": tx_data.get("output_count"),
        "current_next_block_fee": current_next_block,
    }, indent=2)

    explanation = await _ai_complete(SYSTEM_PROMPT_TX, context)
    provider = get_ai_provider()

    return rpc_envelope({
        "txid": txid,
        "explanation": explanation,
        "provider": provider.provider_name,
    }, rpc)


@router.get(
    "/explain/block/{hash_or_height}",
    responses={
        200: {
            "description": "Plain English block summary",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "block_hash": "00000000000000000002a7c...",
                            "height": 883000,
                            "explanation": "Block 883,000 was mined by Foundry USA. It contained 3,241 transactions...",
                            "provider": "azure_openai",
                        },
                        "meta": {"timestamp": "2026-03-15T12:00:00+00:00"},
                    }
                }
            },
        }
    },
)
async def explain_block(
    hash_or_height: str = Path(description="Block hash or height"),
    rpc: BitcoinRPC = Depends(get_rpc),
    _tier: str = Depends(require_api_key),
):
    """Plain English summary of a Bitcoin block."""
    # Resolve height to hash if numeric
    if hash_or_height.isdigit():
        block_hash = rpc.call("getblockhash", int(hash_or_height))
    else:
        block_hash = hash_or_height

    block = rpc.call("getblock", block_hash, 1)  # verbosity 1 = tx list without full details

    # Get recent block stats for comparison
    height = block["height"]
    try:
        stats = rpc.call("getblockstats", height)
    except Exception:
        stats = {}

    context = json.dumps({
        "hash": block_hash,
        "height": height,
        "time": block.get("time"),
        "tx_count": len(block.get("tx", [])),
        "size": block.get("size"),
        "weight": block.get("weight"),
        "difficulty": block.get("difficulty"),
        "total_fee_sats": stats.get("totalfee"),
        "avg_fee_rate": stats.get("avgfeerate"),
        "median_fee_rate": stats.get("feerate_percentiles", [None, None, None])[2] if stats.get("feerate_percentiles") else None,
        "min_fee_rate": stats.get("minfeerate"),
        "max_fee_rate": stats.get("maxfeerate"),
        "subsidy_sats": stats.get("subsidy"),
        "total_out_sats": stats.get("total_out"),
    }, indent=2)

    explanation = await _ai_complete(SYSTEM_PROMPT_BLOCK, context)
    provider = get_ai_provider()

    return rpc_envelope({
        "block_hash": block_hash,
        "height": height,
        "explanation": explanation,
        "provider": provider.provider_name,
    }, rpc)


@router.get(
    "/fees/advice",
    responses={
        200: {
            "description": "Natural language fee advice based on current conditions",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "advice": "Send now at 12 sat/vB — fees are 40% below the 7-day average.",
                            "urgency": "medium",
                            "context": "DCA",
                            "provider": "azure_openai",
                        },
                        "meta": {"timestamp": "2026-03-15T12:00:00+00:00"},
                    }
                }
            },
        }
    },
)
async def fee_advice(
    urgency: str = Query("medium", description="Transaction urgency", enum=["low", "medium", "high"]),
    amount_btc: float | None = Query(None, description="Transaction amount in BTC (optional context)"),
    context: str | None = Query(None, description="Transaction context: DCA, consolidation, payment, etc."),
    rpc: BitcoinRPC = Depends(get_rpc),
    _tier: str = Depends(require_api_key),
):
    """Natural language fee advice powered by AI with live fee data context."""
    fee_estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in fee_estimates}
    snapshots = get_mempool_snapshots()
    landscape = calculate_fee_landscape(fee_dict, snapshots)

    btc_price = get_cached_price()

    user_context = json.dumps({
        "urgency": urgency,
        "amount_btc": amount_btc,
        "transaction_context": context,
        "current_fees": {
            "next_block_sat_vb": fee_dict.get(1, 0),
            "6_blocks_sat_vb": fee_dict.get(6, 0),
            "1_day_sat_vb": fee_dict.get(144, 0),
        },
        "recommendation": landscape["recommendation"],
        "fee_environment": landscape["fee_environment"],
        "trend": landscape["trend"],
        "btc_price_usd": btc_price,
    }, indent=2)

    advice = await _ai_complete(SYSTEM_PROMPT_FEE_ADVICE, user_context, max_tokens=512)
    provider = get_ai_provider()

    # Structured recommendation (machine-readable) alongside natural language
    next_block = fee_dict.get(1, 0)
    recommendation = landscape["recommendation"]

    return rpc_envelope({
        "advice": advice,
        "structured": {
            "recommended_fee_sat_vb": next_block if recommendation == "send" else fee_dict.get(144, 0),
            "action": recommendation,
            "wait": recommendation in ("wait", "urgent_only"),
            "confidence": landscape["confidence"],
            "fee_environment": landscape["fee_environment"]["level"],
            "estimated_savings_pct": round((1 - fee_dict.get(144, 0) / next_block) * 100, 1) if next_block > 0 and fee_dict.get(144, 0) > 0 else 0.0,
        },
        "urgency": urgency,
        "context": context,
        "fee_data": {
            "next_block_sat_vb": next_block,
            "6_blocks_sat_vb": fee_dict.get(6, 0),
            "1_day_sat_vb": fee_dict.get(144, 0),
        },
        "provider": provider.provider_name,
    }, rpc)


@router.get(
    "/chat",
    responses={
        200: {
            "description": "Stateless Bitcoin Q&A with live data context",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "question": "What's happening with fees right now?",
                            "answer": "Current next-block fee is 8 sat/vB, which is low...",
                            "provider": "azure_openai",
                        },
                        "meta": {"timestamp": "2026-03-15T12:00:00+00:00"},
                    }
                }
            },
        }
    },
)
async def chat(
    q: str = Query(..., description="Your Bitcoin question", min_length=3, max_length=500),
    rpc: BitcoinRPC = Depends(get_rpc),
    _tier: str = Depends(require_api_key),
):
    """Stateless Bitcoin Q&A with live blockchain data as context. Rate limited to 10/min."""
    # Gather live context
    info = cached_blockchain_info(rpc)
    fee_estimates = cached_fee_estimates(rpc)
    fee_dict = {e.conf_target: e.fee_rate_sat_vb for e in fee_estimates}
    btc_price = get_cached_price()

    try:
        mempool_info = rpc.call("getmempoolinfo")
    except Exception:
        mempool_info = {}

    live_context = json.dumps({
        "blockchain": {
            "chain": info.get("chain"),
            "height": info.get("blocks"),
            "difficulty": info.get("difficulty"),
            "verification_progress": info.get("verificationprogress"),
        },
        "fees": {
            "next_block_sat_vb": fee_dict.get(1, 0),
            "6_blocks_sat_vb": fee_dict.get(6, 0),
            "1_day_sat_vb": fee_dict.get(144, 0),
        },
        "mempool": {
            "size_txs": mempool_info.get("size"),
            "bytes": mempool_info.get("bytes"),
            "min_fee_rate": mempool_info.get("mempoolminfee"),
        },
        "btc_price_usd": btc_price,
    }, indent=2)

    user_msg = f"Live blockchain context:\n{live_context}\n\nUser question: {q}"
    answer = await _ai_complete(SYSTEM_PROMPT_CHAT, user_msg)
    provider = get_ai_provider()

    return envelope({
        "question": q,
        "answer": answer,
        "provider": provider.provider_name,
    }, height=info.get("blocks"), chain=info.get("chain"))
