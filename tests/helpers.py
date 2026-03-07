"""Test helpers for isolated router testing.

Usage:
    from tests.helpers import make_test_client
    from bitcoin_api.routers.fees import router

    def test_fees_endpoint(mock_rpc):
        client = make_test_client(router, rpc_mock=mock_rpc)
        resp = client.get("/api/v1/fees/6")
        assert resp.status_code == 200
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bitcoin_api.dependencies import get_rpc


def make_test_client(router, rpc_mock=None, prefix="/api/v1"):
    """Create a TestClient for a single router with optional mocks."""
    app = FastAPI()
    app.include_router(router, prefix=prefix)
    if rpc_mock is not None:
        app.dependency_overrides[get_rpc] = lambda: rpc_mock
    return TestClient(app)
