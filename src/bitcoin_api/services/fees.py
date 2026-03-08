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
