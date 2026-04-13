"""IBIT weekend estimate math and canonical snapshot data."""

IBIT_SNAPSHOT = {
    "ticker": "IBIT",
    "date": "2026-04-10",
    "nav": 41.44,
    "close": 41.56,
    "benchmark": 73109.73,
    "premium_discount_pct": 0.30,
    "sponsor_fee_pct": 0.25,
    "shares_outstanding": 1391920000,
    "basket_bitcoin_amount": 22.67,
    "source_url": "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf",
}


def get_ibit_snapshot() -> dict:
    """Return the latest normalized IBIT snapshot used for weekend estimates."""
    return dict(IBIT_SNAPSHOT)


def compute_ibit_estimate(*, btc_price_usd: float, shares: float, snapshot: dict | None = None) -> dict:
    """Estimate IBIT value and BTC exposure from a BTC/USD price anchor."""
    snap = snapshot or IBIT_SNAPSHOT
    btc_per_ibit = snap["nav"] / snap["benchmark"]
    ibit_per_btc = 1 / btc_per_ibit
    estimated_nav_now = btc_price_usd * btc_per_ibit
    estimated_ibit_price_now = snap["close"] * (btc_price_usd / snap["benchmark"])
    estimated_position_value_usd = estimated_ibit_price_now * shares
    estimated_btc_exposure = shares * btc_per_ibit

    return {
        "btc_per_ibit": btc_per_ibit,
        "ibit_per_btc": ibit_per_btc,
        "estimated_nav_now": estimated_nav_now,
        "estimated_ibit_price_now": estimated_ibit_price_now,
        "estimated_position_value_usd": estimated_position_value_usd,
        "estimated_btc_exposure": estimated_btc_exposure,
    }
