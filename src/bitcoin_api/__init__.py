"""Bitcoin REST API — developer-friendly access to your Bitcoin node."""

import json
import logging
import os
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("bitcoin-api")
except PackageNotFoundError:
    __version__ = "0.3.4"


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON for log aggregation tools."""

    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
        })


_log_format = os.environ.get("LOG_FORMAT", "text").lower()

if _log_format == "json":
    _handler = logging.StreamHandler()
    _handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
    logging.root.addHandler(_handler)
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

# Access log gets its own format for structured parsing
_access = logging.getLogger("bitcoin_api.access")
_access.propagate = False
_access_handler = logging.StreamHandler()
if _log_format == "json":
    _access_handler.setFormatter(JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
else:
    _access_handler.setFormatter(logging.Formatter(
        "%(asctime)s ACCESS %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
_access.addHandler(_access_handler)
