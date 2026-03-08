"""Tests for notifications module (Resend email + PostHog analytics)."""

import hashlib
from unittest.mock import patch, MagicMock

from pydantic import SecretStr

from bitcoin_api.config import settings
from bitcoin_api.notifications import send_welcome_email, send_usage_alert, track_registration


def _mock_secret(value: str) -> MagicMock:
    """Create a truthy MagicMock that behaves like SecretStr (no spec — spec=SecretStr is falsy)."""
    m = MagicMock()
    m.get_secret_value.return_value = value
    return m


# --- send_welcome_email ---


@patch.object(settings, "resend_enabled", False)
def test_send_welcome_email_disabled():
    """When resend_enabled=False, returns False and never imports resend."""
    with patch("bitcoin_api.notifications.settings", settings):
        result = send_welcome_email("user@example.com", "btc_abc123", "my-key")
    assert result is False


@patch.object(settings, "resend_enabled", True)
@patch.object(settings, "resend_api_key", _mock_secret("re_test_key"))
def test_send_welcome_email_success():
    """Mock resend module and verify Emails.send() called with correct payload."""
    mock_resend = MagicMock()
    with patch.dict("sys.modules", {"resend": mock_resend}):
        result = send_welcome_email("user@example.com", "btc_abc123", "my-key")

    assert result is True
    mock_resend.Emails.send.assert_called_once()
    payload = mock_resend.Emails.send.call_args[0][0]
    assert payload["to"] == ["user@example.com"]
    assert payload["from"] == settings.resend_from_email
    assert "my-key" in payload["subject"]
    assert "btc_abc123" in payload["html"]


@patch.object(settings, "resend_enabled", True)
@patch.object(settings, "resend_api_key", _mock_secret("re_test_key"))
def test_send_welcome_email_failure():
    """When resend.Emails.send raises, returns False."""
    mock_resend = MagicMock()
    mock_resend.Emails.send.side_effect = RuntimeError("API down")
    with patch.dict("sys.modules", {"resend": mock_resend}):
        result = send_welcome_email("user@example.com", "btc_abc123", "my-key")

    assert result is False


@patch.object(settings, "resend_enabled", True)
@patch.object(settings, "resend_api_key", None)
def test_send_welcome_email_no_api_key():
    """resend_enabled=True but resend_api_key=None returns False."""
    result = send_welcome_email("user@example.com", "btc_abc123", "my-key")
    assert result is False


# --- send_usage_alert ---


@patch.object(settings, "resend_enabled", False)
def test_send_usage_alert_disabled():
    """Returns False when resend is disabled."""
    result = send_usage_alert("user@example.com", 80, "free")
    assert result is False


@patch.object(settings, "resend_enabled", True)
@patch.object(settings, "resend_api_key", _mock_secret("re_test_key"))
def test_send_usage_alert_success():
    """Mock resend and verify correct payload for usage alert."""
    mock_resend = MagicMock()
    with patch.dict("sys.modules", {"resend": mock_resend}):
        result = send_usage_alert("user@example.com", 80, "free")

    assert result is True
    mock_resend.Emails.send.assert_called_once()
    payload = mock_resend.Emails.send.call_args[0][0]
    assert payload["to"] == ["user@example.com"]
    assert "80%" in payload["subject"]
    assert "free" in payload["subject"]


# --- track_registration ---


@patch.object(settings, "posthog_enabled", False)
def test_track_registration_disabled():
    """posthog_enabled=False means posthog is never called."""
    with patch.dict("sys.modules", {"posthog": MagicMock()}) as modules:
        track_registration("user@example.com", "free", "my-key")
        # posthog should not have been touched
        if "posthog" in modules:
            modules["posthog"].capture.assert_not_called()


@patch.object(settings, "posthog_enabled", True)
@patch.object(settings, "posthog_api_key", _mock_secret("phc_test_key"))
def test_track_registration_success():
    """Mock posthog and verify capture() called with HASHED email."""
    mock_posthog = MagicMock()
    with patch.dict("sys.modules", {"posthog": mock_posthog}):
        track_registration("user@example.com", "free", "my-key")

    mock_posthog.capture.assert_called_once()
    call_args = mock_posthog.capture.call_args[0]
    # First arg should be hashed email, NOT raw email
    expected_hash = hashlib.sha256("user@example.com".encode()).hexdigest()
    assert call_args[0] == expected_hash
    assert call_args[0] != "user@example.com"
    # Second arg is event name
    assert call_args[1] == "api_key_registered"
    # Properties
    props = mock_posthog.capture.call_args[0][2]
    assert props["tier"] == "free"
    assert props["label"] == "my-key"
    assert props["email_domain"] == "example.com"


@patch.object(settings, "posthog_enabled", True)
@patch.object(settings, "posthog_api_key", _mock_secret("phc_test_key"))
def test_track_registration_failure():
    """When posthog.capture raises, no exception propagates."""
    mock_posthog = MagicMock()
    mock_posthog.capture.side_effect = RuntimeError("PostHog down")
    with patch.dict("sys.modules", {"posthog": mock_posthog}):
        # Should not raise
        track_registration("user@example.com", "free", "my-key")
