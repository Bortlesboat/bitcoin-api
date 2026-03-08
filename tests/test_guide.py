"""Tests for the guide endpoint."""


def test_guide_returns_envelope(client):
    """Guide should return standard {data, meta} envelope."""
    resp = client.get("/api/v1/guide")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    assert "welcome" in data
    assert "quickstart" in data
    assert "categories" in data
    assert "auth" in data
    assert "links" in data


def test_guide_quickstart_has_steps(client):
    """Guide quickstart should have numbered steps with examples."""
    resp = client.get("/api/v1/guide")
    qs = resp.json()["data"]["quickstart"]
    assert len(qs) >= 3
    assert qs[0]["step"] == 1
    assert "curl" in qs[0]["examples"]


def test_guide_use_case_filter(client):
    """Filtering by use_case should return only that category."""
    resp = client.get("/api/v1/guide?use_case=fees")
    assert resp.status_code == 200
    cats = resp.json()["data"]["categories"]
    assert len(cats) == 1
    assert cats[0]["use_case"] == "fees"
    assert cats[0]["name"] == "Fee Estimation"


def test_guide_lang_filter(client):
    """Filtering by lang should strip other language examples."""
    resp = client.get("/api/v1/guide?lang=python")
    assert resp.status_code == 200
    cats = resp.json()["data"]["categories"]
    for cat in cats:
        for ep in cat["endpoints"]:
            assert "python" in ep["examples"]
            assert "curl" not in ep["examples"]
            assert "javascript" not in ep["examples"]


def test_guide_lang_all(client):
    """lang=all should include all three language examples."""
    resp = client.get("/api/v1/guide?lang=all")
    assert resp.status_code == 200
    ep = resp.json()["data"]["categories"][0]["endpoints"][0]
    assert "curl" in ep["examples"]
    assert "python" in ep["examples"]
    assert "javascript" in ep["examples"]


def test_guide_feature_flagged_categories(client):
    """Feature-flagged categories should appear based on settings."""
    from bitcoin_api.config import settings
    cats = client.get("/api/v1/guide?lang=curl").json()["data"]["categories"]
    use_cases = [c["use_case"] for c in cats]
    if settings.feature_flags.get("prices_router", False):
        assert "prices" in use_cases
    else:
        assert "prices" not in use_cases


def test_guide_auth_shows_rate_limits(client):
    """Auth section should show tier rate limits from settings."""
    from bitcoin_api.config import settings
    auth = client.get("/api/v1/guide").json()["data"]["auth"]
    assert auth["tiers"]["anonymous"]["per_minute"] == settings.rate_limit_anonymous
    assert auth["tiers"]["free"]["per_minute"] == settings.rate_limit_free
    assert auth["method"] == "X-API-Key header"


def test_guide_no_rate_limit(client):
    """Guide endpoint should not be rate limited."""
    for _ in range(35):
        resp = client.get("/api/v1/guide")
        assert resp.status_code == 200
