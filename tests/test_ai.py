"""Tests for AI-powered endpoints (/api/v1/ai/*)."""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest


# --- Provider tests ---


def test_noop_provider_raises():
    """NoopProvider raises AINotConfiguredError."""
    from bitcoin_api.services.ai import NoopProvider, AINotConfiguredError
    import asyncio

    provider = NoopProvider()
    assert provider.provider_name == "none"
    with pytest.raises(AINotConfiguredError):
        asyncio.get_event_loop().run_until_complete(
            provider.complete([{"role": "user", "content": "test"}])
        )


def test_provider_selection_noop():
    """When no AI env vars set, provider is NoopProvider."""
    from bitcoin_api.services.ai import reset_ai_provider, get_ai_provider
    from bitcoin_api.config import settings

    reset_ai_provider()
    # Temporarily clear all AI settings
    orig = (settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url)
    settings.azure_openai_endpoint = None
    settings.azure_openai_key = None
    settings.openai_api_key = None
    settings.ollama_url = None
    try:
        reset_ai_provider()
        provider = get_ai_provider()
        assert provider.provider_name == "none"
    finally:
        settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url = orig
        reset_ai_provider()


def test_provider_selection_ollama():
    """When only OLLAMA_URL is set, provider is OllamaProvider."""
    from bitcoin_api.services.ai import reset_ai_provider, get_ai_provider
    from bitcoin_api.config import settings

    reset_ai_provider()
    orig = (settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url)
    settings.azure_openai_endpoint = None
    settings.azure_openai_key = None
    settings.openai_api_key = None
    settings.ollama_url = "http://localhost:11434"
    try:
        reset_ai_provider()
        provider = get_ai_provider()
        assert provider.provider_name == "ollama"
    finally:
        settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url = orig
        reset_ai_provider()


def test_provider_selection_openai():
    """When OPENAI_API_KEY is set (no Azure), provider is OpenAIProvider."""
    from bitcoin_api.services.ai import reset_ai_provider, get_ai_provider
    from bitcoin_api.config import settings
    from pydantic import SecretStr

    reset_ai_provider()
    orig = (settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url)
    settings.azure_openai_endpoint = None
    settings.azure_openai_key = None
    settings.openai_api_key = SecretStr("sk-test-key")
    settings.ollama_url = None
    try:
        reset_ai_provider()
        provider = get_ai_provider()
        assert provider.provider_name == "openai"
    finally:
        settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url = orig
        reset_ai_provider()


def test_provider_selection_azure():
    """When Azure OpenAI vars are set, provider is AzureOpenAIProvider (highest priority)."""
    from bitcoin_api.services.ai import reset_ai_provider, get_ai_provider
    from bitcoin_api.config import settings
    from pydantic import SecretStr

    reset_ai_provider()
    orig = (settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url)
    settings.azure_openai_endpoint = "https://test.openai.azure.com"
    settings.azure_openai_key = SecretStr("test-key")
    settings.openai_api_key = None
    settings.ollama_url = None
    try:
        reset_ai_provider()
        provider = get_ai_provider()
        assert provider.provider_name == "azure_openai"
    finally:
        settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url = orig
        reset_ai_provider()


# --- Endpoint tests (AI features disabled by default) ---


def test_ai_endpoints_not_registered_when_disabled(client):
    """AI endpoints should 404 when ENABLE_AI_FEATURES=false (default)."""
    from bitcoin_api.config import settings
    # If AI features are enabled in .env, this test checks a different condition
    if settings.enable_ai_features:
        # AI is enabled — endpoint exists but requires auth (403 for anonymous client)
        resp = client.get("/api/v1/ai/chat?q=what+are+fees")
        assert resp.status_code == 403
    else:
        resp = client.get("/api/v1/ai/chat?q=what+are+fees")
        assert resp.status_code == 404


# --- Endpoint tests (with mocked AI provider) ---


@pytest.fixture
def ai_client(mock_rpc):
    """Client with AI router mounted in an isolated FastAPI app (auth bypassed)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from bitcoin_api.dependencies import get_rpc
    from bitcoin_api.auth import require_api_key
    from bitcoin_api.routers.ai import router

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    test_app.dependency_overrides[get_rpc] = lambda: mock_rpc
    test_app.dependency_overrides[require_api_key] = lambda: "free"

    yield TestClient(test_app)


def test_explain_transaction(ai_client):
    """Explain transaction returns explanation text."""
    mock_response = "This transaction sent 0.5 BTC with a fee of 1,000 sats (6 sat/vB). The fee was efficient."

    mock_analysis = MagicMock()
    mock_analysis.model_dump.return_value = {
        "txid": "a" * 64, "size": 225, "vsize": 166, "weight": 661,
        "fee_sat": 1000, "fee_rate_sat_vb": 6.0, "is_segwit": True,
        "is_taproot": False, "has_inscription": False, "input_count": 1, "output_count": 2,
    }

    mock_fee = MagicMock()
    mock_fee.conf_target = 1
    mock_fee.fee_rate_sat_vb = 25.0

    with patch("bitcoin_api.routers.ai.analyze_transaction", return_value=mock_analysis), \
         patch("bitcoin_api.routers.ai.cached_fee_estimates", return_value=[mock_fee]), \
         patch("bitcoin_api.routers.ai.cached_blockchain_info", return_value={"chain": "main", "blocks": 880000}), \
         patch("bitcoin_api.routers.ai.get_ai_provider") as mock_provider_fn:
        provider = MagicMock()
        provider.provider_name = "test"
        provider.complete = AsyncMock(return_value=mock_response)
        mock_provider_fn.return_value = provider

        txid = "a" * 64
        resp = ai_client.get(f"/api/v1/ai/explain/transaction/{txid}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["txid"] == txid
        assert data["explanation"] == mock_response
        assert data["provider"] == "test"


def test_explain_block_by_height(ai_client):
    """Explain block by height returns explanation."""
    mock_response = "Block 880,000 contained 2 transactions with total fees of 25M sats."

    with patch("bitcoin_api.routers.ai.cached_blockchain_info", return_value={"chain": "main", "blocks": 880000}), \
         patch("bitcoin_api.routers.ai.get_ai_provider") as mock_provider_fn:
        provider = MagicMock()
        provider.provider_name = "test"
        provider.complete = AsyncMock(return_value=mock_response)
        mock_provider_fn.return_value = provider

        resp = ai_client.get("/api/v1/ai/explain/block/880000")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["height"] == 880000
        assert data["explanation"] == mock_response


def test_fee_advice(ai_client):
    """Fee advice endpoint returns AI-generated advice."""
    mock_response = "Send now at 12 sat/vB — fees are low and falling."

    with patch("bitcoin_api.routers.ai.get_ai_provider") as mock_provider_fn:
        provider = MagicMock()
        provider.provider_name = "test"
        provider.complete = AsyncMock(return_value=mock_response)
        mock_provider_fn.return_value = provider

        resp = ai_client.get("/api/v1/ai/fees/advice?urgency=high&context=DCA")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["advice"] == mock_response
        assert data["urgency"] == "high"
        assert data["context"] == "DCA"
        assert "fee_data" in data


def test_chat(ai_client):
    """Chat endpoint answers questions with live context."""
    mock_response = "Current next-block fee is 12 sat/vB, which is moderate."

    mock_fee = MagicMock()
    mock_fee.conf_target = 6
    mock_fee.fee_rate_sat_vb = 12.0

    with patch("bitcoin_api.routers.ai.cached_blockchain_info", return_value={"chain": "main", "blocks": 880000, "difficulty": 1e14, "verificationprogress": 0.9999}), \
         patch("bitcoin_api.routers.ai.cached_fee_estimates", return_value=[mock_fee]), \
         patch("bitcoin_api.routers.ai.get_cached_price", return_value=85000.0), \
         patch("bitcoin_api.routers.ai.get_ai_provider") as mock_provider_fn:
        provider = MagicMock()
        provider.provider_name = "test"
        provider.complete = AsyncMock(return_value=mock_response)
        mock_provider_fn.return_value = provider

        resp = ai_client.get("/api/v1/ai/chat?q=What+are+fees+right+now")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["question"] == "What are fees right now"
        assert data["answer"] == mock_response


def test_fee_advice_structured_output(ai_client):
    """Fee advice includes structured machine-readable recommendation."""
    mock_response = "Send now, fees are low."

    mock_fee = MagicMock()
    mock_fee.conf_target = 1
    mock_fee.fee_rate_sat_vb = 5.0

    with patch("bitcoin_api.routers.ai.cached_fee_estimates", return_value=[mock_fee]), \
         patch("bitcoin_api.routers.ai.cached_blockchain_info", return_value={"chain": "main", "blocks": 880000}), \
         patch("bitcoin_api.routers.ai.get_mempool_snapshots", return_value=[]), \
         patch("bitcoin_api.routers.ai.calculate_fee_landscape", return_value={
             "recommendation": "send", "confidence": "high",
             "fee_environment": {"level": "low", "message": "Fees are low."},
             "trend": {"direction": "stable", "mempool_change_pct": 0, "snapshots_available": 0},
         }), \
         patch("bitcoin_api.routers.ai.get_cached_price", return_value=85000.0), \
         patch("bitcoin_api.routers.ai.get_ai_provider") as mock_prov:
        provider = MagicMock()
        provider.provider_name = "test"
        provider.complete = AsyncMock(return_value=mock_response)
        mock_prov.return_value = provider

        resp = ai_client.get("/api/v1/ai/fees/advice?urgency=high&context=payment")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "structured" in data
        s = data["structured"]
        assert "recommended_fee_sat_vb" in s
        assert "action" in s
        assert "wait" in s
        assert isinstance(s["wait"], bool)
        assert "confidence" in s
        assert "fee_environment" in s
        assert "estimated_savings_pct" in s


def test_chat_min_length(ai_client):
    """Chat endpoint rejects too-short questions."""
    resp = ai_client.get("/api/v1/ai/chat?q=hi")
    assert resp.status_code == 422


def test_explain_transaction_invalid_txid(ai_client):
    """Invalid txid returns 422."""
    resp = ai_client.get("/api/v1/ai/explain/transaction/not-a-txid")
    assert resp.status_code == 422


def test_ai_503_when_no_provider(ai_client):
    """AI endpoints return 503 when no provider is configured."""
    from bitcoin_api.services.ai import reset_ai_provider, NoopProvider
    from bitcoin_api.config import settings

    mock_fee = MagicMock()
    mock_fee.conf_target = 6
    mock_fee.fee_rate_sat_vb = 12.0

    # Temporarily force NoopProvider
    orig = (settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url)
    settings.azure_openai_endpoint = None
    settings.azure_openai_key = None
    settings.openai_api_key = None
    settings.ollama_url = None
    reset_ai_provider()

    try:
        with patch("bitcoin_api.routers.ai.cached_blockchain_info", return_value={"chain": "main", "blocks": 880000, "difficulty": 1e14, "verificationprogress": 0.9999}), \
             patch("bitcoin_api.routers.ai.cached_fee_estimates", return_value=[mock_fee]), \
             patch("bitcoin_api.routers.ai.get_cached_price", return_value=85000.0):
            resp = ai_client.get("/api/v1/ai/chat?q=What+are+current+fees")
            assert resp.status_code == 503
    finally:
        settings.azure_openai_endpoint, settings.azure_openai_key, settings.openai_api_key, settings.ollama_url = orig
        reset_ai_provider()
