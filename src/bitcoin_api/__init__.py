"""Bitcoin REST API — developer-friendly access to your Bitcoin node."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("bitcoin-api")
except PackageNotFoundError:
    __version__ = "0.1.0"
