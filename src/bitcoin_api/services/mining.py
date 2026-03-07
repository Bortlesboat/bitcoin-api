"""Mining analysis services: pool identification, hashrate calculation."""

import re

KNOWN_POOLS: dict[str, str] = {
    "Foundry USA": "foundry",
    "/Foundry/": "foundry",
    "AntPool": "antpool",
    "/AntPool/": "antpool",
    "F2Pool": "f2pool",
    "/F2Pool/": "f2pool",
    "ViaBTC": "viabtc",
    "/ViaBTC/": "viabtc",
    "Binance": "binance",
    "/Binance/": "binance",
    "MARA Pool": "mara",
    "/MARA Pool/": "mara",
    "/MaraPool/": "mara",
    "Luxor": "luxor",
    "/Luxor/": "luxor",
    "SBI Crypto": "sbi_crypto",
    "Braiins": "braiins",
    "/Braiins/": "braiins",
    "SlushPool": "braiins",
    "Ocean": "ocean",
    "/ocean.xyz/": "ocean",
    "BTCC": "btcc",
    "BTC.com": "btc.com",
    "SpiderPool": "spiderpool",
    "/SpiderPool/": "spiderpool",
    "Poolin": "poolin",
    "Titan": "titan",
    "/Titan/": "titan",
    "Ultimus": "ultimus",
    "WhitePool": "whitepool",
    "SecPool": "secpool",
    "EMCD": "emcd",
    "KuCoinPool": "kucoinpool",
    "SigmaPool": "sigmapool",
    "Carbon Negative": "carbon_negative",
    "/CarbonNegative/": "carbon_negative",
}

def parse_coinbase_tag(coinbase_hex: str) -> str:
    """Decode coinbase scriptSig hex and match against known pool tags."""
    try:
        decoded = bytes.fromhex(coinbase_hex).decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError):
        return "Unknown"
    for tag, pool_id in KNOWN_POOLS.items():
        if tag.lower() in decoded.lower():
            return pool_id
    return "Unknown"


def extract_coinbase_hex(block_data: dict) -> str:
    """Extract coinbase scriptSig hex from a verbosity-2 block."""
    txs = block_data.get("tx", [])
    if not txs:
        return ""
    coinbase_tx = txs[0]
    vin = coinbase_tx.get("vin", [])
    if not vin:
        return ""
    return vin[0].get("coinbase", "") or vin[0].get("scriptSig", {}).get("hex", "")


def calculate_hashrate(difficulty: float, block_time: float = 600.0) -> float:
    """Calculate network hashrate from difficulty.
    hashrate = difficulty * 2^32 / block_time (in H/s)
    """
    return difficulty * (2 ** 32) / block_time
