"""Prometheus metric definitions on a custom registry."""

import re

from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge

REGISTRY = CollectorRegistry()

# Patterns for normalizing dynamic path segments to prevent label cardinality explosion
_PATH_NORMALIZERS = [
    (re.compile(r"/blocks/[0-9a-fA-F]{64}"), "/blocks/{hash}"),
    (re.compile(r"/blocks/\d+"), "/blocks/{height}"),
    (re.compile(r"/tx/[0-9a-fA-F]{64}"), "/tx/{txid}"),
    (re.compile(r"/address/[a-zA-Z0-9]+"), "/address/{addr}"),
]


def normalize_endpoint(path: str) -> str:
    """Replace dynamic path segments with placeholders for Prometheus labels."""
    for pattern, replacement in _PATH_NORMALIZERS:
        path = pattern.sub(replacement, path)
    return path

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

WS_CONNECTIONS_ACTIVE = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections",
    registry=REGISTRY,
)

API_KEYS_REGISTERED = Gauge(
    "api_keys_registered_total",
    "Total registered API keys",
    registry=REGISTRY,
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_name"],
    registry=REGISTRY,
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_name"],
    registry=REGISTRY,
)

STALE_CACHE_SERVED = Counter(
    "stale_cache_served_total",
    "Stale cache fallbacks served when node is unavailable",
    ["cache_name"],
    registry=REGISTRY,
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    registry=REGISTRY,
)

CIRCUIT_BREAKER_TRIPS = Counter(
    "circuit_breaker_trips_total",
    "Number of times circuit breaker opened",
    registry=REGISTRY,
)

WS_MESSAGES_DROPPED = Counter(
    "websocket_messages_dropped_total",
    "Messages dropped due to slow consumers",
    ["channel"],
    registry=REGISTRY,
)

RATE_LIMIT_BACKEND = Gauge(
    "rate_limit_backend_active",
    "Active rate limit backend (0=memory, 1=redis)",
    registry=REGISTRY,
)
