"""FastAPI dependencies — RPC client singleton, auth, rate limiting."""

from __future__ import annotations

import logging
import threading

from bitcoinlib_rpc import BitcoinRPC

from .config import settings

log = logging.getLogger("bitcoin_api.dependencies")

_rpc: BitcoinRPC | None = None
_rpc_lock = threading.Lock()

_fallback_rpc: BitcoinRPC | None = None
_fallback_rpc_lock = threading.Lock()
_using_fallback = False


def _create_rpc() -> BitcoinRPC:
    return BitcoinRPC(
        host=settings.bitcoin_rpc_host,
        port=settings.bitcoin_rpc_port,
        user=settings.bitcoin_rpc_user,
        password=settings.bitcoin_rpc_password.get_secret_value() if settings.bitcoin_rpc_password else None,
        datadir=settings.bitcoin_datadir,
        timeout=settings.rpc_timeout,
    )


def _create_fallback_rpc() -> BitcoinRPC | None:
    """Create fallback RPC client if configured. Returns None if not configured."""
    if not settings.bitcoin_rpc_fallback_host:
        return None
    return BitcoinRPC(
        host=settings.bitcoin_rpc_fallback_host,
        port=settings.bitcoin_rpc_fallback_port,
        user=settings.bitcoin_rpc_fallback_user,
        password=settings.bitcoin_rpc_fallback_password.get_secret_value() if settings.bitcoin_rpc_fallback_password else None,
        timeout=settings.rpc_timeout,
    )


def _get_fallback_rpc() -> BitcoinRPC | None:
    """Lazy singleton for fallback RPC. Returns None if not configured."""
    global _fallback_rpc
    if settings.bitcoin_rpc_fallback_host is None:
        return None
    if _fallback_rpc is None:
        with _fallback_rpc_lock:
            if _fallback_rpc is None:
                _fallback_rpc = _create_fallback_rpc()
    return _fallback_rpc


def get_rpc() -> BitcoinRPC:
    """Lazy singleton for the Bitcoin RPC connection.

    When the circuit breaker is OPEN and a fallback node is configured,
    returns the fallback RPC connection instead. Automatically fails back
    to primary when circuit breaker transitions to HALF_OPEN or CLOSED.
    """
    global _rpc, _using_fallback
    from .circuit_breaker import CircuitState, rpc_breaker

    state = rpc_breaker.state

    # Circuit is OPEN — use fallback if available
    if state == CircuitState.OPEN:
        fallback = _get_fallback_rpc()
        if fallback is not None:
            if not _using_fallback:
                log.warning("Primary node down — switching to fallback RPC (%s:%d)",
                            settings.bitcoin_rpc_fallback_host, settings.bitcoin_rpc_fallback_port)
                _using_fallback = True
            return fallback

    # Circuit is CLOSED or HALF_OPEN — use primary
    if _using_fallback:
        log.info("Primary node recovered — switching back from fallback RPC")
        _using_fallback = False

    if _rpc is None:
        with _rpc_lock:
            if _rpc is None:
                _rpc = _create_rpc()
    return _rpc


def reset_rpc() -> None:
    """Reset the RPC singleton (called on connection failure to allow recovery)."""
    global _rpc
    with _rpc_lock:
        _rpc = None


def is_using_fallback() -> bool:
    """Return whether the API is currently using the fallback RPC node."""
    return _using_fallback


def get_fallback_status() -> dict:
    """Return fallback node configuration and status for health endpoints."""
    configured = settings.bitcoin_rpc_fallback_host is not None
    status = {
        "configured": configured,
        "active": _using_fallback,
    }
    if configured:
        status["host"] = settings.bitcoin_rpc_fallback_host
        status["port"] = settings.bitcoin_rpc_fallback_port
    return status
