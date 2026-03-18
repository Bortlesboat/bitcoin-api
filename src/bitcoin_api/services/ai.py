"""AI provider abstraction — portable across Azure OpenAI, OpenAI, Ollama, and no-op."""

from __future__ import annotations

import logging
import re
from typing import Protocol

import httpx

from ..config import settings

log = logging.getLogger("bitcoin_api.ai")


class AIProvider(Protocol):
    """Protocol for AI completion providers."""

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str: ...

    @property
    def provider_name(self) -> str: ...


class AzureOpenAIProvider:
    """Azure OpenAI Service provider."""

    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str = "2024-10-21"):
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._deployment = deployment
        self._api_version = api_version

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}"
            f"/chat/completions?api-version={self._api_version}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"api-key": self._api_key, "Content-Type": "application/json"},
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class OpenAIProvider:
    """Direct OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class OllamaProvider:
    """Ollama-compatible provider (OpenAI-compatible /v1/chat/completions)."""

    def __init__(self, base_url: str, model: str = "qwen2.5:14b"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return _strip_think_tags(content)


class NoopProvider:
    """No-op provider — returns 503 when no AI backend is configured."""

    @property
    def provider_name(self) -> str:
        return "none"

    async def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        raise AINotConfiguredError("No AI provider configured. Set AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, or OLLAMA_URL.")


def _strip_think_tags(text: str) -> str:
    """Strip <think>...</think> blocks from model output (qwen3+ thinking mode)."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


class AINotConfiguredError(Exception):
    """Raised when AI features are requested but no provider is configured."""


def _build_provider() -> AIProvider:
    """Build the AI provider from environment configuration.

    Priority: Azure OpenAI > OpenAI > Ollama > Noop.
    """
    if settings.azure_openai_endpoint and settings.azure_openai_key:
        log.info("AI provider: Azure OpenAI (deployment=%s)", settings.azure_openai_deployment)
        return AzureOpenAIProvider(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key.get_secret_value(),
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )
    if settings.openai_api_key:
        log.info("AI provider: OpenAI (model=%s)", settings.openai_model)
        return OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
        )
    if settings.ollama_url:
        log.info("AI provider: Ollama (url=%s, model=%s)", settings.ollama_url, settings.ollama_model)
        return OllamaProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
        )
    log.info("AI provider: none (AI features will return 503)")
    return NoopProvider()


_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """Lazy singleton for the AI provider."""
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider


def reset_ai_provider() -> None:
    """Reset the provider singleton (for testing or config changes)."""
    global _provider
    _provider = None


# --- System prompts ---

SYSTEM_PROMPT_TX = """You are a Bitcoin transaction analyst. Given raw transaction data, explain it in plain English.
Focus on: what happened (payment, consolidation, batch), how many inputs/outputs, fee efficiency,
whether the fee was reasonable compared to current rates. Keep it concise — 2-4 sentences max.
Use sat/vB for fee rates. Never give financial advice."""

SYSTEM_PROMPT_BLOCK = """You are a Bitcoin block analyst. Given block data, provide a brief summary.
Highlight: miner/pool, notable transactions (large value, unusual patterns), total fees,
comparison to typical blocks. Keep it concise — 3-5 sentences max. Never give financial advice."""

SYSTEM_PROMPT_FEE_ADVICE = """You are a Bitcoin fee advisor. Given current fee data, mempool state, and user context,
provide actionable fee advice in plain English. Be specific with numbers. Reference the user's
urgency and transaction type. Keep it concise — 2-4 sentences. Never give financial advice
beyond fee timing."""

SYSTEM_PROMPT_CHAT = """You are a Bitcoin protocol expert embedded in the Satoshi API. You have access to
live blockchain data provided as context. Answer questions about Bitcoin — protocol, transactions,
fees, mining, network. Be accurate, cite specific numbers from the context when relevant.
Keep answers concise. If unsure, say so. Never give financial or investment advice."""
