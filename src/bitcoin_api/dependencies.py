"""FastAPI dependencies — RPC client singleton, auth, rate limiting."""

from __future__ import annotations

from bitcoinlib_rpc import BitcoinRPC

from .config import settings

_rpc: BitcoinRPC | None = None


def get_rpc() -> BitcoinRPC:
    """Lazy singleton for the Bitcoin RPC connection."""
    global _rpc
    if _rpc is None:
        _rpc = BitcoinRPC(
            host=settings.bitcoin_rpc_host,
            port=settings.bitcoin_rpc_port,
            user=settings.bitcoin_rpc_user,
            password=settings.bitcoin_rpc_password,
            datadir=settings.bitcoin_datadir,
        )
    return _rpc
