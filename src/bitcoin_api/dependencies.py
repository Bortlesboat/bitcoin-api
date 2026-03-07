"""FastAPI dependencies — RPC client singleton, auth, rate limiting."""

from __future__ import annotations

import threading

from bitcoinlib_rpc import BitcoinRPC

from .config import settings

_rpc: BitcoinRPC | None = None
_rpc_lock = threading.Lock()


def _create_rpc() -> BitcoinRPC:
    return BitcoinRPC(
        host=settings.bitcoin_rpc_host,
        port=settings.bitcoin_rpc_port,
        user=settings.bitcoin_rpc_user,
        password=settings.bitcoin_rpc_password.get_secret_value() if settings.bitcoin_rpc_password else None,
        datadir=settings.bitcoin_datadir,
        timeout=settings.rpc_timeout,
    )


def get_rpc() -> BitcoinRPC:
    """Lazy singleton for the Bitcoin RPC connection. Resets on connection failure."""
    global _rpc
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
