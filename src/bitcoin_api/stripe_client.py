"""Stripe integration helpers: checkout sessions and webhook verification."""

import logging

from .config import settings

log = logging.getLogger("bitcoin_api.stripe")

_client = None


def get_stripe_client():
    global _client
    if _client is not None:
        return _client
    import stripe
    key = settings.stripe_secret_key
    if key is None:
        raise RuntimeError("Stripe not configured")
    _client = stripe.StripeClient(key.get_secret_value())
    return _client


def create_checkout_session(api_key_hash: str) -> str:
    """Create a Stripe Checkout session and return the URL."""
    client = get_stripe_client()
    session = client.checkout.sessions.create(
        params={
            "mode": "subscription",
            "line_items": [{"price": settings.stripe_price_id, "quantity": 1}],
            "success_url": settings.stripe_success_url,
            "cancel_url": settings.stripe_cancel_url,
            "metadata": {"api_key_hash": api_key_hash},
        }
    )
    return session.url


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify Stripe webhook signature and return the event dict."""
    import stripe
    secret = settings.stripe_webhook_secret
    if secret is None:
        raise RuntimeError("Stripe webhook secret not configured")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, secret.get_secret_value()
        )
    except stripe.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}") from e
    return event
