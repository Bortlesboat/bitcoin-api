"""Transactional email via Resend + analytics events via PostHog."""

import hashlib
import html
import logging
from datetime import datetime, timezone

from bitcoin_api.config import settings

logger = logging.getLogger(__name__)

_notifications_initialized = False


def init_notifications() -> None:
    """One-time initialization of PostHog and Resend clients.

    Call from app lifespan after settings are available.
    """
    global _notifications_initialized
    if _notifications_initialized:
        return

    if settings.posthog_enabled and settings.posthog_api_key:
        try:
            import posthog
            posthog.project_api_key = settings.posthog_api_key.get_secret_value()
            posthog.host = settings.posthog_host
            logger.info("PostHog initialized")
        except Exception as e:
            logger.warning("Failed to initialize PostHog: %s", e)

    if settings.resend_enabled and settings.resend_api_key:
        try:
            import resend
            resend.api_key = settings.resend_api_key.get_secret_value()
            logger.info("Resend initialized")
        except Exception as e:
            logger.warning("Failed to initialize Resend: %s", e)

    _notifications_initialized = True


def send_welcome_email(to_email: str, api_key: str, label: str) -> bool:
    """Send welcome email with API key after registration."""
    if not settings.resend_enabled or not settings.resend_api_key:
        logger.debug("Resend disabled, skipping welcome email")
        return False

    try:
        import resend

        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": f"Your Satoshi API Key — {html.escape(label)}",
            "html": _welcome_html(api_key, html.escape(label)),
        })
        logger.info(f"Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")
        return False


def send_usage_alert(to_email: str, usage_pct: int, tier: str, key_hash: str | None = None) -> bool:
    """Send alert when user approaches rate limit."""
    if not settings.resend_enabled or not settings.resend_api_key:
        return False

    # Check email opt-out preference
    if key_hash:
        try:
            from .db import get_db
            conn = get_db()
            row = conn.execute("SELECT email_opt_out FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
            if row and row[0]:
                return False  # User opted out
        except Exception:
            pass  # Don't block alert on DB errors

    try:
        import resend

        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": f"Satoshi API — You've used {usage_pct}% of your {html.escape(tier)} limit",
            "html": _usage_alert_html(usage_pct, html.escape(tier)),
        })
        logger.info(f"Usage alert sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send usage alert: {e}")
        return False


def track_registration(email: str, tier: str, label: str) -> None:
    """Fire PostHog server-side event on API key registration."""
    if not settings.posthog_enabled or not settings.posthog_api_key:
        return
    try:
        import posthog

        # Hash email to avoid sending PII to PostHog
        hashed_id = hashlib.sha256(email.encode()).hexdigest()
        posthog.capture(hashed_id, "api_key_registered", {
            "tier": tier,
            "label": label,
            "email_domain": email.split("@")[1] if "@" in email else "unknown",
        })
    except Exception:
        pass  # Never fail registration for analytics


def notify_admin_new_registration(
    email: str, label: str, tier: str, utm_source: str | None = None
) -> bool:
    """Send admin alert when a new API key is registered."""
    admin_email = settings.admin_notification_email
    if not admin_email or not settings.resend_enabled or not settings.resend_api_key:
        logger.debug("Admin notification skipped (not configured or Resend disabled)")
        return False

    try:
        import resend

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        source_line = f"<strong>UTM Source:</strong> {html.escape(utm_source)}" if utm_source else "<strong>UTM Source:</strong> <em>none</em>"

        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": [admin_email],
            "subject": f"New Registration: {html.escape(label)} ({html.escape(tier)})",
            "html": _admin_registration_html(
                html.escape(email), html.escape(label),
                html.escape(tier), source_line, timestamp,
            ),
        })
        logger.info(f"Admin registration alert sent for {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin registration alert: {e}")
        return False


_EMAIL_FOOTER = """
    <hr style="border: 1px solid #30363d; margin: 24px 0;">
    <p style="font-size: 11px; color: #8b949e; line-height: 1.5;">
        Satoshi API · <a href="https://bitcoinsapi.com" style="color: #f7931a;">bitcoinsapi.com</a><br>
        Questions? <a href="mailto:api@bitcoinsapi.com" style="color: #f7931a;">api@bitcoinsapi.com</a><br>
        Satoshi API | PO Box 1234, St. Augustine, FL 32084
    </p>
"""


def _welcome_html(api_key: str, label: str) -> str:
    return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; max-width: 600px; margin: 0 auto; background: #0d1117; color: #c9d1d9; padding: 32px; border-radius: 8px;">
    <h1 style="color: #f7931a; font-size: 24px;">Welcome to Satoshi API</h1>
    <p>Your API key <strong>{label}</strong> is ready:</p>
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin: 16px 0; font-family: monospace; word-break: break-all; color: #f7931a;">
        {api_key}
    </div>
    <p style="color: #f85149; font-size: 14px;">Save this key now — it cannot be retrieved later.</p>
    <h2 style="color: #c9d1d9; font-size: 18px;">Quick Start</h2>
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin: 16px 0; font-family: monospace; font-size: 13px; color: #c9d1d9;">
        curl -H "X-API-Key: {api_key}" https://bitcoinsapi.com/api/v1/status
    </div>
    <h2 style="color: #c9d1d9; font-size: 16px;">Popular Endpoints</h2>
    <ul style="font-size: 14px; color: #c9d1d9;">
        <li><a href="https://bitcoinsapi.com/api/v1/fees/recommended" style="color: #f7931a;">/fees/recommended</a> — Fee estimates</li>
        <li><a href="https://bitcoinsapi.com/api/v1/mempool" style="color: #f7931a;">/mempool</a> — Mempool status</li>
        <li><a href="https://bitcoinsapi.com/api/v1/block/latest" style="color: #f7931a;">/block/latest</a> — Latest block</li>
    </ul>
    <p style="font-size: 14px;">Full documentation: <a href="https://bitcoinsapi.com/docs" style="color: #f7931a;">API Docs</a></p>
    <hr style="border: 1px solid #30363d; margin: 24px 0;">
    <p style="font-size: 12px; color: #8b949e;">Free tier: 500 requests/min, 25,000/day. Need more? <a href="https://bitcoinsapi.com/#pricing" style="color: #f7931a;">Upgrade to Pro</a></p>
    <p style="font-size: 11px; color: #8b949e;">This is a transactional email confirming your API key registration.</p>
    {_EMAIL_FOOTER}
</div>
"""


def _usage_alert_html(usage_pct: int, tier: str) -> str:
    return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; max-width: 600px; margin: 0 auto; background: #0d1117; color: #c9d1d9; padding: 32px; border-radius: 8px;">
    <h1 style="color: #f7931a; font-size: 24px;">Usage Alert</h1>
    <p>You've used <strong style="color: #f85149;">{usage_pct}%</strong> of your daily <strong>{tier}</strong> tier limit.</p>
    <p>To avoid interruptions, consider upgrading your plan.</p>
    <a href="https://bitcoinsapi.com/#pricing" style="display: inline-block; background: #f7931a; color: #0d1117; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 16px;">View Plans</a>
    <hr style="border: 1px solid #30363d; margin: 24px 0;">
    <p style="font-size: 12px; color: #8b949e;">To stop receiving these alerts: POST /api/v1/keys/unsubscribe with your API key.</p>
    {_EMAIL_FOOTER}
</div>
"""


def _admin_registration_html(
    email: str, label: str, tier: str, source_line: str, timestamp: str,
) -> str:
    return f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; max-width: 600px; margin: 0 auto; background: #0d1117; color: #c9d1d9; padding: 32px; border-radius: 8px;">
    <h1 style="color: #f7931a; font-size: 24px;">New API Key Registration</h1>
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin: 16px 0; line-height: 1.8;">
        <strong>Email:</strong> {email}<br>
        <strong>Label:</strong> {label}<br>
        <strong>Tier:</strong> {tier}<br>
        {source_line}<br>
        <strong>Registered:</strong> {timestamp}
    </div>
    <div style="background: #1c2128; border-left: 4px solid #f7931a; padding: 12px 16px; margin: 16px 0; border-radius: 0 6px 6px 0;">
        <strong style="color: #f7931a;">Action Required:</strong> Personally reach out to this user within 24 hours.
    </div>
    {_EMAIL_FOOTER}
</div>
"""
