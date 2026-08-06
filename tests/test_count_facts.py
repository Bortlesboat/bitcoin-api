"""Regression tests for the canonical product-facts script."""

from scripts.count_facts import _check_inventory_line, _parse_collection_count


def test_parse_collection_count_reads_pytest_summary():
    assert _parse_collection_count("751 tests collected in 0.42s") == 751


def test_check_inventory_line_reports_only_current_inventory_drift():
    facts = {
        "endpoints": 108,
        "routers": 28,
        "unit_tests": 751,
        "e2e_tests": 21,
        "migrations": 12,
    }
    current = (
        "**Current code-derived inventory:** 108 router-declared API endpoints "
        "across 28 router modules; 751 non-e2e tests + 21 e2e tests; 12 migrations."
    )
    historical = "Earlier sprints expanded the suite from 139 to 207 tests."

    assert _check_inventory_line(f"{current}\n{historical}", facts) == []
    assert _check_inventory_line(current.replace("751", "750"), facts) == [
        "SOW current inventory says 750 non-e2e tests; code collects 751"
    ]
