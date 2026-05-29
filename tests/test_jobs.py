from unittest.mock import MagicMock, patch


def _make_fee_collector_rpc() -> MagicMock:
    rpc = MagicMock()

    def _call(method, *args):
        if method == "getmempoolinfo":
            return {
                "size": 18_500,
                "bytes": 12_400_000,
                "total_fee": 1.75,
            }
        if method == "estimatesmartfee":
            mapping = {
                1: {"feerate": 0.00021, "blocks": 1},
                6: {"feerate": 0.00011, "blocks": 6},
                144: {"feerate": 0.00003, "blocks": 144},
            }
            target = args[0]
            if target not in mapping:
                raise RuntimeError(f"unsupported target {target}")
            return mapping[target]
        if method == "getblockcount":
            return 880_001
        if method == "getblockhash":
            return "000000000000000000001234abcd"
        if method == "getblockstats":
            return {
                "time": 1_709_654_400,
                "txs": 2_450,
                "totalfee": 12_345_678,
                "minfeerate": 2.0,
                "maxfeerate": 44.0,
                "feerate_percentiles": [2.0, 4.0, 9.0, 18.0, 33.0],
            }
        raise AssertionError(f"Unexpected RPC method {method}")

    rpc.call.side_effect = _call
    return rpc


def test_run_fee_collector_iteration_records_block_confirmation_and_estimates():
    from bitcoin_api.db import get_db
    from bitcoin_api.jobs import _run_fee_collector_iteration

    rpc = _make_fee_collector_rpc()

    with patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value={
        "fastestFee": 26,
        "halfHourFee": 14,
        "hourFee": 9,
        "economyFee": 2,
    }), patch("bitcoin_api.jobs.hub.publish"), patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"):
        block_height = _run_fee_collector_iteration(rpc, previous_block_height=880_000)

    assert block_height == 880_001

    conn = get_db()
    block_row = conn.execute(
        "SELECT block_height, block_hash, tx_count, min_feerate, p50_feerate, core_est_1, core_est_6, "
        "core_est_144, mempool_space_est FROM block_confirmations"
    ).fetchone()
    assert block_row is not None
    assert dict(block_row) == {
        "block_height": 880_001,
        "block_hash": "000000000000000000001234abcd",
        "tx_count": 2_450,
        "min_feerate": 2.0,
        "p50_feerate": 9.0,
        "core_est_1": 21.0,
        "core_est_6": 11.0,
        "core_est_144": 3.0,
        "mempool_space_est": 26.0,
    }

    estimate_rows = conn.execute(
        "SELECT source, target, feerate FROM fee_estimates_log ORDER BY source, target"
    ).fetchall()
    assert [tuple(row) for row in estimate_rows] == [
        ("core", 1, 21.0),
        ("core", 6, 11.0),
        ("core", 144, 3.0),
        ("mempool_space", 1, 26.0),
        ("mempool_space", 3, 14.0),
        ("mempool_space", 6, 9.0),
        ("mempool_space", 144, 2.0),
    ]


def test_run_fee_collector_iteration_skips_block_confirmation_without_new_block():
    from bitcoin_api.db import get_db
    from bitcoin_api.jobs import _run_fee_collector_iteration

    rpc = _make_fee_collector_rpc()

    with patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None), patch(
        "bitcoin_api.jobs.hub.publish"
    ), patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"):
        block_height = _run_fee_collector_iteration(rpc, previous_block_height=880_001)

    assert block_height == 880_001

    conn = get_db()
    confirmation_count = conn.execute("SELECT COUNT(*) FROM block_confirmations").fetchone()[0]
    estimate_rows = conn.execute(
        "SELECT source, target, feerate FROM fee_estimates_log ORDER BY source, target"
    ).fetchall()

    assert confirmation_count == 0
    assert [tuple(row) for row in estimate_rows] == [
        ("core", 1, 21.0),
        ("core", 6, 11.0),
        ("core", 144, 3.0),
    ]
