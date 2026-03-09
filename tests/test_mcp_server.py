"""Tests for the MCP server tools and helpers."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Ensure MCP_INTERNAL_API_KEY is set before importing the module
os.environ.setdefault("MCP_INTERNAL_API_KEY", "test-internal-key")

from bitcoin_api.routers.mcp_server import (  # noqa: E402
    _extract_data,
    _get_client,
    _internal_headers,
    mcp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.text = str(json_data)
    return resp


def _error_response(status_code, detail="error"):
    """Create a mock httpx.Response that raises on raise_for_status."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = detail
    request = MagicMock(spec=httpx.Request)
    request.url = "http://test"
    resp.request = request
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"HTTP {status_code}", request=request, response=resp
    )
    return resp


@pytest.fixture
def mock_client():
    """Patch _get_client to return a mock AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.is_closed = False
    with patch("bitcoin_api.routers.mcp_server._get_client", return_value=client):
        yield client


# ---------------------------------------------------------------------------
# _extract_data tests
# ---------------------------------------------------------------------------

class TestExtractData:
    def test_unwraps_envelope(self):
        result = {"data": {"fee": 10}, "meta": {"request_id": "abc"}}
        assert _extract_data(result) == {"fee": 10}

    def test_fallback_no_data_key(self):
        result = {"fee": 10, "blocks": 6}
        assert _extract_data(result) == {"fee": 10, "blocks": 6}

    def test_empty_data(self):
        result = {"data": {}, "meta": {}}
        assert _extract_data(result) == {}

    def test_data_is_list(self):
        result = {"data": [1, 2, 3]}
        assert _extract_data(result) == [1, 2, 3]


# ---------------------------------------------------------------------------
# _internal_headers tests
# ---------------------------------------------------------------------------

class TestInternalHeaders:
    def test_returns_api_key_when_set(self):
        with patch("bitcoin_api.routers.mcp_server._INTERNAL_KEY", "my-secret"):
            headers = _internal_headers()
            assert headers == {"X-API-Key": "my-secret"}

    def test_returns_empty_when_no_key(self):
        with patch("bitcoin_api.routers.mcp_server._INTERNAL_KEY", ""):
            headers = _internal_headers()
            assert headers == {}


# ---------------------------------------------------------------------------
# _get_client tests
# ---------------------------------------------------------------------------

class TestGetClient:
    def test_returns_client(self):
        with patch("bitcoin_api.routers.mcp_server._client", None):
            client = _get_client()
            assert isinstance(client, httpx.AsyncClient)

    def test_singleton_behavior(self):
        with patch("bitcoin_api.routers.mcp_server._client", None):
            c1 = _get_client()
            # Patch _client to the returned value to simulate module state
            with patch("bitcoin_api.routers.mcp_server._client", c1):
                c2 = _get_client()
                assert c1 is c2

    def test_recreates_closed_client(self):
        closed = MagicMock(spec=httpx.AsyncClient)
        closed.is_closed = True
        with patch("bitcoin_api.routers.mcp_server._client", closed):
            new_client = _get_client()
            assert new_client is not closed


# ---------------------------------------------------------------------------
# get_api_info tests
# ---------------------------------------------------------------------------

class TestGetApiInfo:
    @pytest.mark.anyio
    async def test_returns_correct_structure(self):
        from bitcoin_api import __version__
        result = await mcp._tool_manager._tools["get_api_info"].fn()
        assert result["name"] == "Satoshi API"
        assert result["version"] == __version__
        assert result["endpoints"] == 87
        assert result["tools_exposed"] == 17
        assert "website" in result
        assert "docs" in result
        assert "source" in result


# ---------------------------------------------------------------------------
# get_situation_summary tests
# ---------------------------------------------------------------------------

class TestGetSituationSummary:
    @pytest.mark.anyio
    async def test_aggregates_three_calls(self, mock_client):
        health_resp = _mock_response({"data": {"blocks": 880000, "chain": "main"}})
        fees_resp = _mock_response({"data": {
            "recommendation": "send",
            "reasoning": "Low fees",
            "fee_environment": {"level": "low"},
            "current_fees": {"next_block": 5, "six_blocks": 3, "one_day": 1},
            "trend": {"direction": "falling"},
        }})
        mempool_resp = _mock_response({"data": {
            "size": 15000, "bytes": 8500000, "congestion": "normal",
        }})

        mock_client.get = AsyncMock(side_effect=[health_resp, fees_resp, mempool_resp])

        result = await mcp._tool_manager._tools["get_situation_summary"].fn()

        assert result["height"] == 880000
        assert result["chain"] == "main"
        assert result["fee_recommendation"] == "send"
        assert result["fee_reasoning"] == "Low fees"
        assert result["fee_environment"] == "low"
        assert result["next_block_fee_sat_vb"] == 5
        assert result["mempool_tx_count"] == 15000
        assert result["trend"] == "falling"
        assert mock_client.get.call_count == 3


# ---------------------------------------------------------------------------
# get_fee_recommendation tests
# ---------------------------------------------------------------------------

class TestGetFeeRecommendation:
    @pytest.mark.anyio
    async def test_returns_landscape_data(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"recommendation": "wait", "confidence": "high"}
        }))
        result = await mcp._tool_manager._tools["get_fee_recommendation"].fn()
        assert result["recommendation"] == "wait"
        assert result["confidence"] == "high"


# ---------------------------------------------------------------------------
# get_fee_estimates tests
# ---------------------------------------------------------------------------

class TestGetFeeEstimates:
    @pytest.mark.anyio
    async def test_returns_fees(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"estimates": [{"target": 1, "rate": 20}]}
        }))
        result = await mcp._tool_manager._tools["get_fee_estimates"].fn()
        assert "estimates" in result


# ---------------------------------------------------------------------------
# estimate_transaction_cost tests
# ---------------------------------------------------------------------------

class TestEstimateTransactionCost:
    @pytest.mark.anyio
    async def test_passes_params(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"vsize": 141, "costs": {}}
        }))
        result = await mcp._tool_manager._tools["estimate_transaction_cost"].fn(
            inputs=2, outputs=3, input_type="p2tr", output_type="p2tr"
        )
        assert result["vsize"] == 141
        # Verify params were passed
        call_kwargs = mock_client.get.call_args
        assert call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")


# ---------------------------------------------------------------------------
# get_mempool_status tests
# ---------------------------------------------------------------------------

class TestGetMempoolStatus:
    @pytest.mark.anyio
    async def test_returns_mempool_data(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"size": 15000, "bytes": 8500000, "congestion": "normal"}
        }))
        result = await mcp._tool_manager._tools["get_mempool_status"].fn()
        assert result["size"] == 15000
        assert result["congestion"] == "normal"


# ---------------------------------------------------------------------------
# get_latest_block tests
# ---------------------------------------------------------------------------

class TestGetLatestBlock:
    @pytest.mark.anyio
    async def test_returns_block(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"height": 880000, "hash": "abc123"}
        }))
        result = await mcp._tool_manager._tools["get_latest_block"].fn()
        assert result["height"] == 880000


# ---------------------------------------------------------------------------
# get_block tests
# ---------------------------------------------------------------------------

class TestGetBlock:
    @pytest.mark.anyio
    async def test_with_height(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"height": 880000, "tx_count": 3500}
        }))
        result = await mcp._tool_manager._tools["get_block"].fn(height_or_hash="880000")
        assert result["height"] == 880000
        mock_client.get.assert_called_once()
        assert "/blocks/880000" in str(mock_client.get.call_args)

    @pytest.mark.anyio
    async def test_with_hash(self, mock_client):
        block_hash = "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72f9a4670"
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"height": 880000, "hash": block_hash}
        }))
        result = await mcp._tool_manager._tools["get_block"].fn(height_or_hash=block_hash)
        assert result["height"] == 880000


# ---------------------------------------------------------------------------
# get_transaction tests
# ---------------------------------------------------------------------------

class TestGetTransaction:
    @pytest.mark.anyio
    async def test_valid_txid(self, mock_client):
        txid = "a" * 64
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"txid": txid, "vsize": 166}
        }))
        result = await mcp._tool_manager._tools["get_transaction"].fn(txid=txid)
        assert result["txid"] == txid
        assert result["vsize"] == 166

    @pytest.mark.anyio
    async def test_invalid_txid(self, mock_client):
        result = await mcp._tool_manager._tools["get_transaction"].fn(txid="not-a-txid")
        assert "error" in result
        assert "Invalid txid" in result["error"]
        mock_client.get.assert_not_called()


# ---------------------------------------------------------------------------
# get_address_balance tests
# ---------------------------------------------------------------------------

class TestGetAddressBalance:
    @pytest.mark.anyio
    async def test_requires_api_key(self, mock_client):
        result = await mcp._tool_manager._tools["get_address_balance"].fn(
            address="bc1qtest", api_key=""
        )
        assert "error" in result
        assert "API key required" in result["error"]

    @pytest.mark.anyio
    async def test_with_api_key(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"balance_btc": 0.5, "utxo_count": 3}
        }))
        result = await mcp._tool_manager._tools["get_address_balance"].fn(
            address="bc1qtest", api_key="user-key-123"
        )
        assert result["balance_btc"] == 0.5

    @pytest.mark.anyio
    async def test_http_error_handling(self, mock_client):
        mock_client.get = AsyncMock(return_value=_error_response(404, "Not found"))
        result = await mcp._tool_manager._tools["get_address_balance"].fn(
            address="bc1qinvalid", api_key="user-key-123"
        )
        assert "error" in result
        assert "404" in result["error"]


# ---------------------------------------------------------------------------
# plan_transaction tests
# ---------------------------------------------------------------------------

class TestPlanTransaction:
    @pytest.mark.anyio
    async def test_default_params(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"cost_tiers": {}, "recommendation": "send"}
        }))
        result = await mcp._tool_manager._tools["plan_transaction"].fn()
        assert result["recommendation"] == "send"

    @pytest.mark.anyio
    async def test_custom_params(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"cost_tiers": {}, "recommendation": "wait"}
        }))
        result = await mcp._tool_manager._tools["plan_transaction"].fn(
            profile="batch_payout", inputs=5, outputs=10,
            address_type="taproot", currency="usd"
        )
        # Verify params were passed correctly
        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["profile"] == "batch_payout"
        assert params["inputs"] == 5
        assert params["outputs"] == 10
        assert params["address_type"] == "taproot"
        assert params["currency"] == "usd"


# ---------------------------------------------------------------------------
# broadcast_transaction tests
# ---------------------------------------------------------------------------

class TestBroadcastTransaction:
    @pytest.mark.anyio
    async def test_requires_api_key(self, mock_client):
        result = await mcp._tool_manager._tools["broadcast_transaction"].fn(
            raw_tx_hex="0200abcd", api_key=""
        )
        assert "error" in result
        assert "API key required" in result["error"]

    @pytest.mark.anyio
    async def test_invalid_hex(self, mock_client):
        result = await mcp._tool_manager._tools["broadcast_transaction"].fn(
            raw_tx_hex="not-hex!!", api_key="my-key"
        )
        assert "error" in result
        assert "Invalid hex" in result["error"]

    @pytest.mark.anyio
    async def test_successful_broadcast(self, mock_client):
        txid = "a" * 64
        mock_client.post = AsyncMock(return_value=_mock_response({
            "data": {"txid": txid}
        }))
        result = await mcp._tool_manager._tools["broadcast_transaction"].fn(
            raw_tx_hex="0200abcdef01", api_key="my-key"
        )
        assert result["txid"] == txid

    @pytest.mark.anyio
    async def test_broadcast_http_error(self, mock_client):
        mock_client.post = AsyncMock(return_value=_error_response(400, "bad tx"))
        result = await mcp._tool_manager._tools["broadcast_transaction"].fn(
            raw_tx_hex="0200abcdef01", api_key="my-key"
        )
        assert "error" in result
        assert "Broadcast failed" in result["error"]


# ---------------------------------------------------------------------------
# get_fee_landscape tests
# ---------------------------------------------------------------------------

class TestGetFeeLandscape:
    @pytest.mark.anyio
    async def test_returns_landscape(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"recommendation": "send", "scenarios": {}}
        }))
        result = await mcp._tool_manager._tools["get_fee_landscape"].fn()
        assert result["recommendation"] == "send"


# ---------------------------------------------------------------------------
# get_mining_info tests
# ---------------------------------------------------------------------------

class TestGetMiningInfo:
    @pytest.mark.anyio
    async def test_returns_mining_data(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"hashrate": 800e18, "difficulty": 110e12}
        }))
        result = await mcp._tool_manager._tools["get_mining_info"].fn()
        assert result["hashrate"] == 800e18


# ---------------------------------------------------------------------------
# get_network_info tests
# ---------------------------------------------------------------------------

class TestGetNetworkInfo:
    @pytest.mark.anyio
    async def test_returns_network_data(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"connections": 125, "relayfee": 0.00001}
        }))
        result = await mcp._tool_manager._tools["get_network_info"].fn()
        assert result["connections"] == 125


# ---------------------------------------------------------------------------
# get_supply_info tests
# ---------------------------------------------------------------------------

class TestGetSupplyInfo:
    @pytest.mark.anyio
    async def test_returns_supply_data(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"circulating": 19687500, "percent_mined": 93.75}
        }))
        result = await mcp._tool_manager._tools["get_supply_info"].fn()
        assert result["circulating"] == 19687500


# ---------------------------------------------------------------------------
# search tests
# ---------------------------------------------------------------------------

class TestSearch:
    @pytest.mark.anyio
    async def test_search_by_height(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"height": 880000}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query="880000")
        assert result["type"] == "block"
        assert result["data"]["height"] == 880000

    @pytest.mark.anyio
    async def test_search_by_block_hash(self, mock_client):
        block_hash = "0000000000000000000" + "a" * 45
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"hash": block_hash, "height": 880000}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query=block_hash)
        assert result["type"] == "block"

    @pytest.mark.anyio
    async def test_search_by_txid(self, mock_client):
        txid = "b" * 64  # doesn't start with 00000000
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"txid": txid, "vsize": 166}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query=txid)
        assert result["type"] == "transaction"

    @pytest.mark.anyio
    async def test_search_by_address(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"isvalid": True, "address": "bc1qtest"}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query="bc1qtest")
        assert result["type"] == "address"

    @pytest.mark.anyio
    async def test_search_unknown_input(self, mock_client):
        # Query must not start with any address prefix (bc1, 1, 3, tb1, m, n, 2)
        result = await mcp._tool_manager._tools["search"].fn(query="xyz-unknown-query")
        assert "error" in result

    @pytest.mark.anyio
    async def test_search_txid_not_found_falls_back_to_block(self, mock_client):
        """When a 64-hex query fails as tx, it should try as block hash."""
        txid = "c" * 64  # doesn't start with 00000000

        # First call (tx lookup) fails, second call (block lookup) succeeds
        tx_resp = _error_response(404, "Not found")
        block_resp = _mock_response({"data": {"height": 500000}})
        mock_client.get = AsyncMock(side_effect=[tx_resp, block_resp])

        result = await mcp._tool_manager._tools["search"].fn(query=txid)
        assert result["type"] == "block"

    @pytest.mark.anyio
    async def test_search_block_hash_fails_falls_to_tx(self, mock_client):
        """Block hash starting with 00000000 that's not a block should try as tx."""
        query = "00000000" + "f" * 56

        # First call (block) fails, second (tx) succeeds
        block_resp = _error_response(404, "Not found")
        tx_resp = _mock_response({"data": {"txid": query}})
        mock_client.get = AsyncMock(side_effect=[block_resp, tx_resp])

        result = await mcp._tool_manager._tools["search"].fn(query=query)
        assert result["type"] == "transaction"

    @pytest.mark.anyio
    async def test_search_64hex_not_found_anywhere(self, mock_client):
        """64-char hex not found as tx or block should return error."""
        query = "d" * 64
        mock_client.get = AsyncMock(return_value=_error_response(404, "Not found"))

        result = await mcp._tool_manager._tools["search"].fn(query=query)
        assert "error" in result
        assert "Not found" in result["error"]

    @pytest.mark.anyio
    async def test_search_strips_whitespace(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"height": 100}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query="  100  ")
        assert result["type"] == "block"

    @pytest.mark.anyio
    async def test_search_testnet_address(self, mock_client):
        mock_client.get = AsyncMock(return_value=_mock_response({
            "data": {"isvalid": True, "address": "tb1qtest"}
        }))
        result = await mcp._tool_manager._tools["search"].fn(query="tb1qtest")
        assert result["type"] == "address"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.anyio
    async def test_api_get_raises_on_http_error(self, mock_client):
        """Tools that don't catch HTTPStatusError should propagate it."""
        mock_client.get = AsyncMock(return_value=_error_response(500, "Server Error"))
        with pytest.raises(httpx.HTTPStatusError):
            await mcp._tool_manager._tools["get_fee_estimates"].fn()

    @pytest.mark.anyio
    async def test_get_transaction_invalid_txid_no_api_call(self, mock_client):
        """Invalid txid should return error without calling API."""
        result = await mcp._tool_manager._tools["get_transaction"].fn(txid="short")
        assert "error" in result
        mock_client.get.assert_not_called()
