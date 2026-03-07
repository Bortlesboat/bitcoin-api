"""Bitcoin REST API — developer-friendly access to your Bitcoin node."""

import logging
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("bitcoin-api")
except PackageNotFoundError:
    __version__ = "0.2.1"

# Configure logging once at package import
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
# Access log gets its own format for structured parsing
_access = logging.getLogger("bitcoin_api.access")
_access.propagate = False
_access_handler = logging.StreamHandler()
_access_handler.setFormatter(logging.Formatter(
    "%(asctime)s ACCESS %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
_access.addHandler(_access_handler)
