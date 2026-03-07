"""Prometheus metric definitions on a custom registry."""

from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status", "tier"],
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

BLOCK_HEIGHT = Gauge(
    "bitcoin_block_height",
    "Current Bitcoin block height from background job",
    registry=REGISTRY,
)

JOB_ERRORS = Counter(
    "background_job_errors_total",
    "Total background job errors",
    registry=REGISTRY,
)
