from unittest.mock import MagicMock, patch


def _make_fee_collector_rpc(
    *,
    block_count: int = 880_001,
    block_hashes: dict[int, str] | None = None,
) -> MagicMock:
    rpc = MagicMock()
    block_hashes = block_hashes or {}

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
            return block_count
        if method == "getblockhash":
            return block_hashes.get(args[0], f"hash-{args[0]}")
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

    with (
        patch(
            "bitcoin_api.jobs._fetch_mempool_space_fees",
            return_value={
                "fastestFee": 26,
                "halfHourFee": 14,
                "hourFee": 9,
                "economyFee": 2,
            },
        ),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(rpc, previous_block_height=880_000)

    assert state == (880_001, "hash-880001")

    conn = get_db()
    block_row = conn.execute(
        "SELECT block_height, block_hash, tx_count, min_feerate, p50_feerate, core_est_1, core_est_6, "
        "core_est_144, mempool_space_est FROM block_confirmations"
    ).fetchone()
    assert block_row is not None
    assert dict(block_row) == {
        "block_height": 880_001,
        "block_hash": "hash-880001",
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

    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(
            rpc,
            previous_block_height=880_001,
            previous_block_hash="hash-880001",
        )

    assert state == (880_001, "hash-880001")

    conn = get_db()
    confirmation_count = conn.execute(
        "SELECT COUNT(*) FROM block_confirmations"
    ).fetchone()[0]
    estimate_rows = conn.execute(
        "SELECT source, target, feerate FROM fee_estimates_log ORDER BY source, target"
    ).fetchall()

    assert confirmation_count == 0
    assert [tuple(row) for row in estimate_rows] == [
        ("core", 1, 21.0),
        ("core", 6, 11.0),
        ("core", 144, 3.0),
    ]


def test_run_fee_collector_iteration_captures_every_missed_block():
    from bitcoin_api.db import get_db
    from bitcoin_api.jobs import _run_fee_collector_iteration

    rpc = _make_fee_collector_rpc(block_count=880_002)

    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(rpc, previous_block_height=880_000)

    assert state == (880_002, "hash-880002")
    conn = get_db()
    rows = conn.execute(
        "SELECT block_height, block_hash FROM block_confirmations ORDER BY block_height"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (880_001, "hash-880001"),
        (880_002, "hash-880002"),
    ]


def test_run_fee_collector_iteration_refreshes_same_height_reorg():
    from bitcoin_api.db import get_db
    from bitcoin_api.jobs import _run_fee_collector_iteration

    rpc = _make_fee_collector_rpc(block_hashes={880_001: "active-chain-hash"})

    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(
            rpc,
            previous_block_height=880_001,
            previous_block_hash="stale-chain-hash",
        )

    assert state == (880_001, "active-chain-hash")
    conn = get_db()
    row = conn.execute(
        "SELECT block_height, block_hash FROM block_confirmations"
    ).fetchone()
    assert tuple(row) == (880_001, "active-chain-hash")


def test_build_fee_estimate_entries_ignores_malformed_provider_values():
    from bitcoin_api.jobs import _build_fee_estimate_entries

    entries = _build_fee_estimate_entries(
        12.0,
        8.0,
        2.0,
        mempool_space_fees={
            "fastestFee": "not-a-number",
            "halfHourFee": None,
            "hourFee": 7,
            "economyFee": -1,
        },
    )

    assert entries == [
        ("core", 1, 12.0),
        ("core", 6, 8.0),
        ("core", 144, 2.0),
        ("mempool_space", 6, 7.0),
    ]


def test_run_fee_collector_iteration_removes_orphaned_rows_after_backward_reorg():
    from bitcoin_api.db import get_db, record_block_confirmation
    from bitcoin_api.jobs import _run_fee_collector_iteration

    for height in (880_002, 880_003):
        record_block_confirmation(
            block_height=height,
            block_hash=f"orphan-{height}",
            block_time="2024-03-05 12:00:00",
            tx_count=1,
            total_fees_sat=1,
            min_feerate=1.0,
            max_feerate=1.0,
            p10_feerate=1.0,
            p25_feerate=1.0,
            p50_feerate=1.0,
            p75_feerate=1.0,
            p90_feerate=1.0,
        )

    rpc = _make_fee_collector_rpc(block_count=880_001)
    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(
            rpc,
            previous_block_height=880_003,
            previous_block_hash="orphan-880003",
        )

    assert state == (880_001, "hash-880001")
    rows = (
        get_db()
        .execute(
            "SELECT block_height, block_hash FROM block_confirmations ORDER BY block_height"
        )
        .fetchall()
    )
    assert [tuple(row) for row in rows] == [(880_001, "hash-880001")]


def test_run_fee_collector_iteration_resumes_from_persisted_tip_after_restart():
    from bitcoin_api.db import get_db, record_block_confirmation
    from bitcoin_api.jobs import _run_fee_collector_iteration

    record_block_confirmation(
        block_height=880_000,
        block_hash="hash-880000",
        block_time="2024-03-05 12:00:00",
        tx_count=1,
        total_fees_sat=1,
        min_feerate=1.0,
        max_feerate=1.0,
        p10_feerate=1.0,
        p25_feerate=1.0,
        p50_feerate=1.0,
        p75_feerate=1.0,
        p90_feerate=1.0,
    )

    rpc = _make_fee_collector_rpc(block_count=880_002)
    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(rpc)

    assert state == (880_002, "hash-880002")
    rows = (
        get_db()
        .execute(
            "SELECT block_height, block_hash FROM block_confirmations ORDER BY block_height"
        )
        .fetchall()
    )
    assert [tuple(row) for row in rows] == [
        (880_000, "hash-880000"),
        (880_001, "hash-880001"),
        (880_002, "hash-880002"),
    ]


def test_run_fee_collector_iteration_replaces_deep_reorg_suffix():
    from bitcoin_api.db import get_db, record_block_confirmation
    from bitcoin_api.jobs import _run_fee_collector_iteration

    for height, block_hash in (
        (880_000, "hash-880000"),
        (880_001, "orphan-880001"),
        (880_002, "orphan-880002"),
    ):
        record_block_confirmation(
            block_height=height,
            block_hash=block_hash,
            block_time="2024-03-05 12:00:00",
            tx_count=1,
            total_fees_sat=1,
            min_feerate=1.0,
            max_feerate=1.0,
            p10_feerate=1.0,
            p25_feerate=1.0,
            p50_feerate=1.0,
            p75_feerate=1.0,
            p90_feerate=1.0,
        )

    rpc = _make_fee_collector_rpc(block_count=880_002)
    with (
        patch("bitcoin_api.jobs._fetch_mempool_space_fees", return_value=None),
        patch("bitcoin_api.jobs.hub.publish"),
        patch("bitcoin_api.jobs.BLOCK_HEIGHT.set"),
    ):
        state = _run_fee_collector_iteration(
            rpc,
            previous_block_height=880_002,
            previous_block_hash="orphan-880002",
        )

    assert state == (880_002, "hash-880002")
    rows = (
        get_db()
        .execute(
            "SELECT block_height, block_hash FROM block_confirmations ORDER BY block_height"
        )
        .fetchall()
    )
    assert [tuple(row) for row in rows] == [
        (880_000, "hash-880000"),
        (880_001, "hash-880001"),
        (880_002, "hash-880002"),
    ]


def test_fetch_mempool_space_fees_rejects_non_object_json():
    from bitcoin_api.jobs import _fetch_mempool_space_fees

    response = MagicMock()
    response.__enter__.return_value.read.return_value = b"[]"
    with patch("bitcoin_api.jobs.urllib.request.urlopen", return_value=response):
        assert _fetch_mempool_space_fees() is None
