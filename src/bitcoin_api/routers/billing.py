"""Stripe billing endpoints: checkout, webhook, status, cancel."""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..auth import authenticate, clear_auth_cache
from ..config import settings
from ..db import get_db
from ..middleware import get_client_ip
from ..models import envelope
from ..rate_limit import check_rate_limit_raw
from ..stripe_client import create_checkout_session, verify_webhook_signature

log = logging.getLogger("bitcoin_api.billing")

router = APIRouter(prefix="/billing", tags=["Billing"])


def _require_stripe():
    """Raise 503 if Stripe is not configured."""
    if settings.stripe_secret_key is None:
        raise HTTPException(status_code=503, detail="Billing not configured.")
    if not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Billing not yet configured: missing Stripe price ID.")


def _require_auth(request: Request) -> str:
    """Require a valid free+ API key. Returns key_hash."""
    key_info = authenticate(request)
    if key_info.tier in ("anonymous", "invalid"):
        raise HTTPException(status_code=401, detail="API key required for billing endpoints.")
    return key_info.key_hash


@router.post(
    "/checkout",
    summary="Create Stripe checkout session",
    description="Creates a Stripe Checkout session for Pro tier subscription. Returns the checkout URL.",
    responses={
        200: {"description": "Checkout URL"},
        401: {"description": "API key required"},
        503: {"description": "Billing not configured"},
    },
)
async def create_checkout(request: Request):
    _require_stripe()
    key_hash = _require_auth(request)
    url = create_checkout_session(key_hash)
    return envelope({"checkout_url": url})


@router.post(
    "/webhook",
    summary="Stripe webhook handler",
    description="Processes Stripe webhook events for subscription lifecycle management.",
    responses={200: {"description": "Event processed"}},
    include_in_schema=False,
)
async def stripe_webhook(request: Request):
    _require_stripe()
    # Per-IP rate limit on webhook (60 req/min) — Stripe is excluded from global
    # rate limiting, so we enforce a separate limit here.
    client_ip = get_client_ip(request)
    wh_limit = check_rate_limit_raw(f"webhook:{client_ip}", 60)
    if not wh_limit.allowed:
        raise HTTPException(status_code=429, detail="Too many webhook requests.")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = verify_webhook_signature(payload, sig)
    except ValueError as e:
        log.warning("Webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"] if isinstance(event, dict) else event.type
    db = get_db()

    if event_type == "checkout.session.completed":
        session = event["data"]["object"] if isinstance(event, dict) else event.data.object
        api_key_hash = session.get("metadata", {}).get("api_key_hash")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        if api_key_hash:
            db.execute(
                "UPDATE api_keys SET tier = 'pro', stripe_customer_id = ? WHERE key_hash = ?",
                (customer_id, api_key_hash),
            )
            db.execute(
                "INSERT OR REPLACE INTO subscriptions (api_key_hash, stripe_customer_id, stripe_subscription_id, status) VALUES (?, ?, ?, 'active')",
                (api_key_hash, customer_id, subscription_id),
            )
            db.commit()
            clear_auth_cache()
            log.info("Pro tier activated for key_hash=%s...", api_key_hash[:8])

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub = event["data"]["object"] if isinstance(event, dict) else event.data.object
        sub_id = sub.get("id")
        status = sub.get("status", "")
        if status in ("canceled", "unpaid") or event_type == "customer.subscription.deleted":
            db.execute(
                "UPDATE subscriptions SET status = 'canceled' WHERE stripe_subscription_id = ?",
                (sub_id,),
            )
            # Downgrade tier
            row = db.execute(
                "SELECT api_key_hash FROM subscriptions WHERE stripe_subscription_id = ?",
                (sub_id,),
            ).fetchone()
            if row:
                db.execute("UPDATE api_keys SET tier = 'free' WHERE key_hash = ?", (row[0],))
            db.commit()
            clear_auth_cache()
            log.info("Subscription %s canceled/deleted", sub_id)

    elif event_type == "invoice.payment_failed":
        event_id = event["id"] if isinstance(event, dict) else getattr(event, "id", "?")
        log.warning("Payment failed for event %s — Stripe will retry", event_id)

    return JSONResponse({"status": "ok"})


@router.get(
    "/status",
    summary="Subscription status",
    description="Returns current subscription status for the authenticated API key.",
    responses={
        200: {"description": "Subscription info"},
        401: {"description": "API key required"},
        503: {"description": "Billing not configured"},
    },
)
async def subscription_status(request: Request):
    _require_stripe()
    key_hash = _require_auth(request)
    db = get_db()
    row = db.execute(
        "SELECT stripe_subscription_id, status, created_at FROM subscriptions WHERE api_key_hash = ?",
        (key_hash,),
    ).fetchone()
    if row:
        data = {"subscription_id": row[0], "status": row[1], "created_at": row[2]}
    else:
        data = {"subscription_id": None, "status": "none", "created_at": None}
    return envelope(data)


@router.post(
    "/cancel",
    summary="Cancel subscription",
    description="Cancels the Pro subscription at the end of the current billing period.",
    responses={
        200: {"description": "Cancellation confirmed"},
        401: {"description": "API key required"},
        404: {"description": "No active subscription"},
        503: {"description": "Billing not configured"},
    },
)
async def cancel_subscription(request: Request):
    _require_stripe()
    key_hash = _require_auth(request)
    db = get_db()
    row = db.execute(
        "SELECT stripe_subscription_id, status FROM subscriptions WHERE api_key_hash = ? AND status = 'active'",
        (key_hash,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No active subscription found.")

    _cancel_at_period_end(row[0])

    db.execute(
        "UPDATE subscriptions SET status = 'cancel_at_period_end' WHERE stripe_subscription_id = ?",
        (row[0],),
    )
    db.commit()
    return envelope({"status": "cancel_at_period_end", "subscription_id": row[0]})


def _cancel_at_period_end(subscription_id: str):
    """Tell Stripe to cancel at period end."""
    from ..stripe_client import get_stripe_client
    client = get_stripe_client()
    client.subscriptions.update(subscription_id, params={"cancel_at_period_end": True})
