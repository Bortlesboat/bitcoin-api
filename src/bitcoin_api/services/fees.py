"""Fee analysis business logic — extracted from routers/fees.py."""

# Max block weight (4 million weight units)
MAX_BLOCK_WEIGHT = 4_000_000

# Transaction size/weight constants by script type
TX_OVERHEAD = 10.5  # version(4) + marker(0.25) + flag(0.25) + locktime(4) + vin_count(1) + vout_count(1)
INPUT_WEIGHTS = {
    "p2pkh": 592,     # 148 bytes * 4
    "p2wpkh": 272,    # 68 vB * 4 (41 non-witness + 27 witness weight)
    "p2sh": 700,      # ~175 bytes * 4 (varies with script)
    "p2wsh": 400,     # ~100 vB * 4
    "p2tr": 230,      # ~57.5 vB * 4 (key-path spend)
}
OUTPUT_WEIGHTS = {
    "p2pkh": 136,     # 34 bytes * 4
    "p2wpkh": 124,    # 31 bytes * 4
    "p2sh": 128,      # 32 bytes * 4
    "p2wsh": 172,     # 43 bytes * 4
    "p2tr": 172,      # 43 bytes * 4
}


def analyze_mempool_blocks(raw_mempool: dict) -> list[dict]:
    """Project the next N blocks from raw mempool data, sorted by fee rate descending."""
    txs = []
    for txid, entry in raw_mempool.items():
        fee_sat = entry.get("fees", {}).get("base", 0) * 1e8
        weight = entry.get("weight", entry.get("vsize", 0) * 4)
        if weight > 0:
            fee_rate = fee_sat / (weight / 4)  # sat/vB
            txs.append((fee_rate, weight, fee_sat))

    txs.sort(key=lambda x: x[0], reverse=True)

    blocks = []
    block_weight = 0
    block_txs = []

    for fee_rate, weight, fee_sat in txs:
        if block_weight + weight > MAX_BLOCK_WEIGHT:
            if block_txs:
                rates = [t[0] for t in block_txs]
                s = sorted(rates)
                mid = len(s) // 2
                median = (s[mid - 1] + s[mid]) / 2 if len(s) % 2 == 0 else s[mid]
                blocks.append({
                    "block_index": len(blocks),
                    "min_fee_rate": round(min(rates), 2),
                    "max_fee_rate": round(max(rates), 2),
                    "median_fee_rate": round(median, 2),
                    "tx_count": len(block_txs),
                    "total_weight": block_weight,
                    "total_fees_sat": round(sum(t[2] for t in block_txs)),
                })
            block_weight = 0
            block_txs = []
            if len(blocks) >= 8:
                break
        block_weight += weight
        block_txs.append((fee_rate, weight, fee_sat))

    # Don't forget the last partial block
    if block_txs and len(blocks) < 8:
        rates = [t[0] for t in block_txs]
        s = sorted(rates)
        mid = len(s) // 2
        median = (s[mid - 1] + s[mid]) / 2 if len(s) % 2 == 0 else s[mid]
        blocks.append({
            "block_index": len(blocks),
            "min_fee_rate": round(min(rates), 2),
            "max_fee_rate": round(max(rates), 2),
            "median_fee_rate": round(median, 2),
            "tx_count": len(block_txs),
            "total_weight": block_weight,
            "total_fees_sat": round(sum(t[2] for t in block_txs)),
        })

    return blocks


def calculate_fee_landscape(fee_dict: dict, snapshots: list) -> dict:
    """Compute fee landscape: recommendation, trend analysis, scenarios.

    Args:
        fee_dict: {conf_target: fee_rate_sat_vb} mapping
        snapshots: list of mempool snapshots from the snapshot buffer

    Returns:
        dict with recommendation, confidence, reasoning, trend, current_fees, scenarios
    """
    next_block = fee_dict.get(1, 0)
    six_block = fee_dict.get(6, 0)
    day_fee = fee_dict.get(144, 0)

    # Trend analysis from snapshot buffer
    trend = "unknown"
    trend_pct = 0.0
    if len(snapshots) >= 2:
        oldest = snapshots[0]
        newest = snapshots[-1]
        old_size = oldest.get("mempool_bytes", 0)
        new_size = newest.get("mempool_bytes", 0)
        if old_size > 0:
            trend_pct = round(((new_size - old_size) / old_size) * 100, 1)
        if trend_pct > 5:
            trend = "rising"
        elif trend_pct < -5:
            trend = "falling"
        else:
            trend = "stable"

    # Decision logic
    typical_vsize = 140  # P2WPKH 1-in-2-out
    if next_block <= 5:
        recommendation = "send"
        confidence = "high"
        reasoning = f"Fees are very low at {next_block} sat/vB. Great time to send."
    elif next_block <= 20:
        if trend == "falling":
            recommendation = "send"
            confidence = "medium"
            reasoning = f"Fees are moderate at {next_block} sat/vB and falling ({trend_pct}%). Good time to send."
        else:
            recommendation = "send"
            confidence = "medium"
            reasoning = f"Fees are moderate at {next_block} sat/vB. Acceptable to send now."
    elif next_block <= 50:
        if trend == "falling":
            recommendation = "send"
            confidence = "medium"
            savings_pct = round((1 - day_fee / next_block) * 100) if next_block > 0 else 0
            reasoning = (
                f"Fees are elevated at {next_block} sat/vB but mempool is draining ({trend_pct}%). "
                f"Waiting could save ~{savings_pct}% if you can wait."
            )
        else:
            recommendation = "wait"
            confidence = "medium"
            savings_pct = round((1 - day_fee / next_block) * 100) if next_block > 0 else 0
            reasoning = (
                f"Fees are elevated at {next_block} sat/vB. "
                f"Waiting for low-priority could save ~{savings_pct}%."
            )
    else:
        recommendation = "urgent_only"
        confidence = "high"
        savings_pct = round((1 - day_fee / next_block) * 100) if next_block > 0 else 0
        reasoning = (
            f"Fees are high at {next_block} sat/vB. Only send if urgent. "
            f"Waiting could save ~{savings_pct}%."
        )

    scenarios = {
        "send_now": {
            "fee_rate": next_block,
            "total_sats": round(next_block * typical_vsize),
            "total_btc": round(next_block * typical_vsize / 1e8, 8),
            "target": "next block",
        },
        "wait_1hr": {
            "fee_rate": six_block,
            "total_sats": round(six_block * typical_vsize),
            "total_btc": round(six_block * typical_vsize / 1e8, 8),
            "target": "~6 blocks (~1 hour)",
        },
        "wait_low": {
            "fee_rate": day_fee,
            "total_sats": round(day_fee * typical_vsize),
            "total_btc": round(day_fee * typical_vsize / 1e8, 8),
            "target": "~144 blocks (~1 day)",
        },
    }
    if next_block > 0 and day_fee > 0:
        scenarios["wait_low"]["savings_vs_now_pct"] = round((1 - day_fee / next_block) * 100, 1)
    if next_block > 0 and six_block > 0:
        scenarios["wait_1hr"]["savings_vs_now_pct"] = round((1 - six_block / next_block) * 100, 1)

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "reasoning": reasoning,
        "trend": {
            "direction": trend,
            "mempool_change_pct": trend_pct,
            "snapshots_available": len(snapshots),
        },
        "current_fees": {
            "next_block": next_block,
            "six_blocks": six_block,
            "one_day": day_fee,
        },
        "scenarios": scenarios,
    }


def estimate_tx_fees(fee_dict: dict, inputs: int, outputs: int,
                     input_type: str = "p2wpkh", output_type: str = "p2wpkh") -> dict:
    """Estimate transaction size and fee cost.

    Args:
        fee_dict: {conf_target: fee_rate_sat_vb} mapping
        inputs: number of inputs
        outputs: number of outputs
        input_type: script type for inputs
        output_type: script type for outputs

    Returns:
        dict with vsize, weight, breakdown, and fee scenarios
    """
    in_weight = INPUT_WEIGHTS.get(input_type, INPUT_WEIGHTS["p2wpkh"])
    out_weight = OUTPUT_WEIGHTS.get(output_type, OUTPUT_WEIGHTS["p2wpkh"])

    total_weight = round(TX_OVERHEAD * 4) + (inputs * in_weight) + (outputs * out_weight)
    estimated_vsize = (total_weight + 3) // 4  # ceil division

    targets = {
        "next_block": (1, "~10 min"),
        "3_blocks": (3, "~30 min"),
        "6_blocks": (6, "~1 hour"),
        "1_day": (144, "~1 day"),
    }
    fee_scenarios = {}
    for label, (target, desc) in targets.items():
        rate = fee_dict.get(target, 0)
        total_sats = round(rate * estimated_vsize)
        fee_scenarios[label] = {
            "fee_rate_sat_vb": rate,
            "total_fee_sats": total_sats,
            "total_fee_btc": round(total_sats / 1e8, 8),
            "conf_target": target,
            "estimated_time": desc,
        }

    return {
        "estimated_vsize": estimated_vsize,
        "estimated_weight": total_weight,
        "inputs": inputs,
        "outputs": outputs,
        "input_type": input_type,
        "output_type": output_type,
        "breakdown": {
            "overhead_weight": round(TX_OVERHEAD * 4),
            "per_input_weight": in_weight,
            "per_output_weight": out_weight,
            "total_input_weight": inputs * in_weight,
            "total_output_weight": outputs * out_weight,
        },
        "fee_scenarios": fee_scenarios,
    }


def summarize_fee_history(rows: list[dict]) -> dict | None:
    """Compute summary statistics for fee history rows."""
    if not rows:
        return None

    fees = [r["next_block_fee"] for r in rows if r.get("next_block_fee")]
    if fees:
        min_fee = min(fees)
        max_fee = max(fees)
        avg_fee = round(sum(fees) / len(fees), 2)
        cheapest_row = min(rows, key=lambda r: r.get("next_block_fee") or float("inf"))
        cheapest_ts = cheapest_row.get("ts")
    else:
        min_fee = max_fee = avg_fee = 0
        cheapest_ts = None

    return {
        "min_next_block_fee": min_fee,
        "max_next_block_fee": max_fee,
        "avg_next_block_fee": avg_fee,
        "cheapest_time_utc": cheapest_ts,
        "datapoints_count": len(rows),
    }


# --- Transaction profiles for /fees/plan ---

PROFILES = {
    "simple_send": {"inputs": 1, "outputs": 2, "input_type": "p2wpkh", "output_type": "p2wpkh",
                    "description": "Standard payment (1 input, 2 outputs, SegWit)"},
    "exchange_withdrawal": {"inputs": 1, "outputs": 1, "input_type": "p2wpkh", "output_type": "p2wpkh",
                            "description": "Single withdrawal (1 input, 1 output, SegWit)"},
    "batch_payout": {"inputs": 1, "outputs": 10, "input_type": "p2wpkh", "output_type": "p2wpkh",
                     "description": "Batch payout (1 input, 10 outputs, SegWit)"},
    "consolidation": {"inputs": 10, "outputs": 1, "input_type": "p2wpkh", "output_type": "p2wpkh",
                      "description": "UTXO consolidation (10 inputs, 1 output, SegWit)"},
}

# Map developer-friendly names to script types
ADDRESS_TYPE_MAP = {
    "segwit": "p2wpkh",
    "taproot": "p2tr",
    "legacy": "p2pkh",
    "p2sh": "p2sh",
    "p2wsh": "p2wsh",
    # Also accept raw script type names
    "p2wpkh": "p2wpkh",
    "p2tr": "p2tr",
    "p2pkh": "p2pkh",
}


def _resolve_address_type(address_type: str) -> str:
    """Resolve a developer-friendly address type to a script type."""
    return ADDRESS_TYPE_MAP.get(address_type.lower(), "p2wpkh")


def _sats_to_usd(sats: int | float, btc_price: float) -> float:
    """Convert satoshis to USD, rounded to 4 decimal places."""
    return round(sats / 1e8 * btc_price, 4)


def plan_transaction(
    fee_dict: dict,
    snapshots: list,
    fee_history_rows: list,
    *,
    profile: str | None = None,
    inputs: int | None = None,
    outputs: int | None = None,
    address_type: str = "segwit",
    btc_price: float | None = None,
) -> dict:
    """Enhanced transaction cost planner.

    Combines estimate_tx_fees + calculate_fee_landscape + historical comparison
    into a single actionable response.

    Args:
        fee_dict: {conf_target: fee_rate_sat_vb} mapping
        snapshots: mempool snapshots for trend analysis
        fee_history_rows: recent fee history for historical comparison
        profile: preset profile name (overrides inputs/outputs/address_type)
        inputs: number of inputs (default from profile or 1)
        outputs: number of outputs (default from profile or 2)
        address_type: segwit, taproot, or legacy (default segwit)
    """
    # Resolve profile or use explicit params
    if profile and profile in PROFILES:
        p = PROFILES[profile]
        inputs = inputs or p["inputs"]
        outputs = outputs or p["outputs"]
        script_type = _resolve_address_type(address_type) if address_type != "segwit" else p["input_type"]
    else:
        inputs = inputs or 1
        outputs = outputs or 2
        script_type = _resolve_address_type(address_type)
        profile = None

    # Get size estimation
    tx_estimate = estimate_tx_fees(fee_dict, inputs, outputs, script_type, script_type)

    # Get landscape recommendation
    landscape = calculate_fee_landscape(fee_dict, snapshots)

    # Build cost tiers with human-readable names
    vsize = tx_estimate["estimated_vsize"]
    next_block = fee_dict.get(1, 0)
    three_block = fee_dict.get(3, 0)
    six_block = fee_dict.get(6, 0)
    day_fee = fee_dict.get(144, 0)

    def _build_tier(fee_rate: float, time_label: str, target: int) -> dict:
        total_sats = round(fee_rate * vsize)
        tier = {
            "fee_rate_sat_vb": fee_rate,
            "total_fee_sats": total_sats,
            "total_fee_btc": round(total_sats / 1e8, 8),
            "estimated_time": time_label,
            "conf_target": target,
        }
        if btc_price:
            tier["total_fee_usd"] = _sats_to_usd(total_sats, btc_price)
        return tier

    cost_tiers = {
        "immediate": _build_tier(next_block, "~10 minutes", 1),
        "standard": _build_tier(three_block, "~30 minutes", 3),
        "patient": _build_tier(six_block, "~1 hour", 6),
        "opportunistic": _build_tier(day_fee, "~1 day", 144),
    }

    # Delay savings percentage (how much you save by waiting for opportunistic vs immediate)
    delay_savings_pct = round((1 - day_fee / next_block) * 100, 1) if next_block > 0 and day_fee > 0 else 0.0

    # Historical comparison — what would this tx have cost at the cheapest point recently?
    historical_comparison = None
    if fee_history_rows:
        history_summary = summarize_fee_history(fee_history_rows)
        if history_summary and history_summary["min_next_block_fee"] > 0:
            min_hist_fee = history_summary["min_next_block_fee"]
            historical_cost = round(min_hist_fee * vsize)
            current_cost = round(next_block * vsize)
            pct_diff = round((1 - min_hist_fee / next_block) * 100, 1) if next_block > 0 else 0.0
            historical_comparison = {
                "current_fee_rate": next_block,
                "cheapest_fee_rate": min_hist_fee,
                "cheapest_cost_sats": historical_cost,
                "cheapest_time_utc": history_summary["cheapest_time_utc"],
                "current_premium_pct": pct_diff,
                "period_hours": len(fee_history_rows),
                "avg_fee_rate": history_summary["avg_next_block_fee"],
            }
            if btc_price:
                historical_comparison["cheapest_cost_usd"] = _sats_to_usd(historical_cost, btc_price)
                historical_comparison["current_cost_usd"] = _sats_to_usd(current_cost, btc_price)

    result = {
        "transaction": {
            "inputs": inputs,
            "outputs": outputs,
            "address_type": address_type,
            "script_type": script_type,
            "estimated_vsize": vsize,
            "estimated_weight": tx_estimate["estimated_weight"],
        },
        "cost_tiers": cost_tiers,
        "recommendation": landscape["recommendation"],
        "recommendation_confidence": 1.0 if landscape["confidence"] == "high" else 0.6 if landscape["confidence"] == "medium" else 0.3,
        "reasoning": landscape["reasoning"],
        "delay_savings_pct": delay_savings_pct,
        "trend": landscape["trend"],
    }

    if profile:
        result["profile"] = profile
        result["profile_description"] = PROFILES[profile]["description"]

    if historical_comparison:
        result["historical_comparison"] = historical_comparison

    result["available_profiles"] = list(PROFILES.keys())

    if btc_price:
        result["btc_price_usd"] = btc_price

    return result


def simulate_fee_savings(fee_history_rows: list, *, vsize: int = 141, days: int | None = None, btc_price: float | None = None) -> dict:
    """Simulate how much a user would save by using optimal fee timing.

    Compares "always send at current next-block fee" vs "send at the cheapest
    fee in each time window" over the historical period.

    Args:
        fee_history_rows: fee history data from DB
        vsize: transaction vsize for cost calculation (default: P2WPKH 1-in-2-out = 141 vB)
        days: label for the period (informational)

    Returns:
        dict with savings stats, total costs, and proof points
    """
    if not fee_history_rows:
        return {
            "period_hours": 0,
            "datapoints": 0,
            "message": "No fee history data available. Data accumulates over time.",
        }

    fees = [r["next_block_fee"] for r in fee_history_rows if r.get("next_block_fee") and r["next_block_fee"] > 0]
    if not fees:
        return {
            "period_hours": 0,
            "datapoints": 0,
            "message": "No valid fee data in the requested period.",
        }

    # "Always send now" = average fee rate across all datapoints
    avg_fee = sum(fees) / len(fees)
    avg_cost_sats = round(avg_fee * vsize)

    # "Optimal timing" = send at the minimum fee rate
    min_fee = min(fees)
    optimal_cost_sats = round(min_fee * vsize)

    # Savings per transaction
    savings_sats = avg_cost_sats - optimal_cost_sats
    savings_pct = round((1 - min_fee / avg_fee) * 100, 1) if avg_fee > 0 else 0.0

    # Extrapolate monthly savings (assume 1 tx/day)
    hours_covered = len(fees)  # rough proxy since each row ~ 1 interval
    monthly_savings_sats = round(savings_sats * 30) if savings_sats > 0 else 0

    # Find cheapest window
    cheapest_row = min(fee_history_rows, key=lambda r: r.get("next_block_fee") or float("inf"))
    most_expensive_row = max(fee_history_rows, key=lambda r: r.get("next_block_fee") or 0)

    result = {
        "period_hours": hours_covered,
        "datapoints": len(fees),
        "reference_vsize": vsize,
        "always_send_now": {
            "avg_fee_rate": round(avg_fee, 3),
            "avg_cost_sats": avg_cost_sats,
            "avg_cost_btc": round(avg_cost_sats / 1e8, 8),
        },
        "optimal_timing": {
            "best_fee_rate": round(min_fee, 3),
            "best_cost_sats": optimal_cost_sats,
            "best_cost_btc": round(optimal_cost_sats / 1e8, 8),
            "best_time_utc": cheapest_row.get("ts"),
        },
        "savings_per_tx": {
            "sats": savings_sats,
            "btc": round(savings_sats / 1e8, 8),
            "percent": savings_pct,
        },
        "monthly_projection": {
            "txs_assumed": 30,
            "total_savings_sats": monthly_savings_sats,
            "total_savings_btc": round(monthly_savings_sats / 1e8, 8),
        },
        "fee_range": {
            "min": round(min_fee, 3),
            "max": round(max(fees), 3),
            "avg": round(avg_fee, 3),
            "spread_pct": round((max(fees) - min_fee) / avg_fee * 100, 1) if avg_fee > 0 else 0.0,
        },
        "worst_time_utc": most_expensive_row.get("ts"),
    }

    if btc_price:
        result["btc_price_usd"] = btc_price
        result["always_send_now"]["avg_cost_usd"] = _sats_to_usd(avg_cost_sats, btc_price)
        result["optimal_timing"]["best_cost_usd"] = _sats_to_usd(optimal_cost_sats, btc_price)
        result["savings_per_tx"]["usd"] = _sats_to_usd(savings_sats, btc_price)
        result["monthly_projection"]["total_savings_usd"] = _sats_to_usd(monthly_savings_sats, btc_price)

    return result
