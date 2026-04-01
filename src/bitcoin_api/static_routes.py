"""Static file routes: landing page, robots.txt, sitemap, decision pages, admin dashboard."""

import re
import secrets
from pathlib import Path

from fastapi import Cookie, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from . import __version__

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
_LANDING_PAGE = _STATIC_DIR / "index.html"
_404_PAGE = _STATIC_DIR / "404.html"
_HISTORY_DIR = _STATIC_DIR / "history"
_HISTORY_PAGES = {"index", "block", "tx", "address"}


def _render_html(path: Path) -> HTMLResponse | None:
    """Render a static HTML file with runtime substitutions."""
    if not path.exists():
        return None

    from .config import settings

    html = path.read_text(encoding="utf-8")
    ph_key = settings.posthog_api_key.get_secret_value() if settings.posthog_api_key else ""
    html = html.replace("__POSTHOG_API_KEY__", ph_key)
    if '/static/js/site-helpers.js' not in html:
        helper_tag = '<script src="/static/js/site-helpers.js"></script>'
        html = re.sub(r"</body>", helper_tag + "\n</body>", html, count=1, flags=re.IGNORECASE)
    nonce = secrets.token_urlsafe(16)
    html = re.sub(r"<script(?![^>]*\bnonce=)", f'<script nonce="{nonce}"', html, flags=re.IGNORECASE)

    # Keep public navigation safe when the History Explorer is disabled.
    if not settings.enable_history_explorer:
        html = html.replace('href="/history"', 'href="/guide"')

    response = HTMLResponse(html)
    response.headers["X-CSP-Nonce"] = nonce
    return response


def _serve_404():
    """Return branded 404 page with PostHog key injected."""
    response = _render_html(_404_PAGE)
    if response is not None:
        response.status_code = 404
        return response
    return Response(status_code=404)


def register_static_routes(app: FastAPI):
    """Register landing page, robots.txt, sitemap, healthz, and static decision pages."""

    from starlette.staticfiles import StaticFiles
    _js_dir = _STATIC_DIR / "js"
    if _js_dir.is_dir():
        app.mount("/static/js", StaticFiles(directory=str(_js_dir)), name="static-js")

    _PUBLIC_METHODS = ["GET", "HEAD"]

    @app.api_route("/", methods=_PUBLIC_METHODS, include_in_schema=False)
    def root():
        return _render_html(_LANDING_PAGE) or _serve_404()

    @app.api_route("/api-docs", methods=_PUBLIC_METHODS, include_in_schema=False)
    def api_docs_redirect():
        """Avoid maintaining a second docs surface; send users to live Swagger docs."""
        return RedirectResponse(url="/docs", status_code=308)

    @app.api_route("/.well-known/mcp/server-card.json", methods=_PUBLIC_METHODS, include_in_schema=False)
    def mcp_server_card():
        """MCP server card for Smithery discovery."""
        p = _STATIC_DIR / ".well-known" / "mcp" / "server-card.json"
        if p.exists():
            import json
            return Response(
                p.read_text(encoding="utf-8"),
                media_type="application/json",
            )
        return Response(status_code=404)

    @app.api_route("/favicon.ico", methods=_PUBLIC_METHODS, include_in_schema=False)
    def favicon():
        p = _STATIC_DIR / "favicon.ico"
        if p.exists():
            return Response(p.read_bytes(), media_type="image/x-icon")
        return Response(status_code=204)

    @app.api_route("/robots.txt", methods=_PUBLIC_METHODS, include_in_schema=False)
    def robots_txt():
        p = _STATIC_DIR / "robots.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return Response("User-agent: *\nAllow: /\n", media_type="text/plain")

    @app.api_route("/llms.txt", methods=_PUBLIC_METHODS, include_in_schema=False)
    def llms_txt():
        p = _STATIC_DIR / "llms.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()

    @app.api_route("/llms-full.txt", methods=_PUBLIC_METHODS, include_in_schema=False)
    def llms_full_txt():
        p = _STATIC_DIR / "llms-full.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()

    @app.api_route("/sitemap.xml", methods=_PUBLIC_METHODS, include_in_schema=False)
    def sitemap_xml():
        p = _STATIC_DIR / "sitemap.xml"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="application/xml")
        return _serve_404()

    _IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}

    @app.api_route("/{filename}.{ext}", methods=_PUBLIC_METHODS, include_in_schema=False)
    def static_asset(filename: str, ext: str):
        """Serve static assets (images + IndexNow verification key) from the static directory."""
        # Prevent path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            return _serve_404()
        suffix = f".{ext}"
        # IndexNow verification key (32-char hex + .txt)
        if suffix == ".txt" and len(filename) == 32:
            p = _STATIC_DIR / f"{filename}{suffix}"
            if p.exists():
                return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
            return _serve_404()
        if suffix not in _IMAGE_TYPES:
            return _serve_404()
        p = _STATIC_DIR / f"{filename}{suffix}"
        if p.exists():
            return Response(p.read_bytes(), media_type=_IMAGE_TYPES[suffix])
        return _serve_404()

    def _check_admin_key(
        key: str = Query(""),
        x_admin_key: str | None = Header(None),
        admin_token: str | None = Cookie(None),
    ) -> str:
        """Extract admin key from header, cookie, or query param (in that order)."""
        return x_admin_key or admin_token or key

    @app.get("/admin/dashboard", include_in_schema=False)
    def admin_dashboard(
        key: str = Query(""),
        x_admin_key: str | None = Header(None),
        admin_token: str | None = Cookie(None),
    ):
        """Admin analytics dashboard — accepts X-Admin-Key header, admin_token cookie, or ?key= query param."""
        from .config import settings
        if not settings.admin_api_key:
            raise HTTPException(status_code=403, detail="Admin not configured")
        resolved_key = _check_admin_key(key, x_admin_key, admin_token)
        if not resolved_key or not secrets.compare_digest(resolved_key, settings.admin_api_key.get_secret_value()):
            raise HTTPException(status_code=403, detail="Invalid admin key")
        p = _STATIC_DIR / "admin-dashboard.html"
        response = _render_html(p) or _serve_404()
        # Set cookie so subsequent page loads don't need the key in the URL
        if isinstance(response, HTMLResponse) and not admin_token:
            response.set_cookie("admin_token", resolved_key, httponly=True, secure=True, samesite="strict", max_age=86400)
        return response

    @app.get("/admin/founder", include_in_schema=False)
    def founder_dashboard(
        key: str = Query(""),
        x_admin_key: str | None = Header(None),
        admin_token: str | None = Cookie(None),
    ):
        """Founder analytics dashboard — accepts X-Admin-Key header, admin_token cookie, or ?key= query param."""
        from .config import settings
        if not settings.admin_api_key:
            raise HTTPException(status_code=403, detail="Admin not configured")
        resolved_key = _check_admin_key(key, x_admin_key, admin_token)
        if not resolved_key or not secrets.compare_digest(resolved_key, settings.admin_api_key.get_secret_value()):
            raise HTTPException(status_code=403, detail="Invalid admin key")
        p = _STATIC_DIR / "founder-dashboard.html"
        response = _render_html(p) or _serve_404()
        if isinstance(response, HTMLResponse) and not admin_token:
            response.set_cookie("admin_token", resolved_key, httponly=True, secure=True, samesite="strict", max_age=86400)
        return response

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        """Process-alive check (no RPC call). Use for container healthchecks."""
        return {"status": "ok"}

    @app.api_route("/history", methods=_PUBLIC_METHODS, include_in_schema=False)
    def history_index():
        """Serve the History Explorer index page (feature-flag gated)."""
        from .config import settings
        if not settings.enable_history_explorer:
            return _serve_404()
        p = _HISTORY_DIR / "index.html"
        return _render_html(p) or _serve_404()

    @app.api_route("/history/{page}", methods=_PUBLIC_METHODS, include_in_schema=False)
    def history_page(page: str):
        """Serve History Explorer sub-pages and static assets."""
        from .config import settings
        if not settings.enable_history_explorer:
            return _serve_404()
        # Known HTML pages
        if page in _HISTORY_PAGES:
            p = _HISTORY_DIR / f"{page}.html"
            return _render_html(p) or _serve_404()
        # Static assets (.json, .css, .js) — with path traversal protection
        if "/" in page or "\\" in page or ".." in page:
            return _serve_404()
        resolved = (_HISTORY_DIR / page).resolve()
        if not str(resolved).startswith(str(_HISTORY_DIR.resolve())):
            return _serve_404()
        if resolved.exists() and resolved.suffix in (".json", ".css", ".js"):
            media_types = {".json": "application/json", ".css": "text/css", ".js": "application/javascript"}
            return Response(resolved.read_text(encoding="utf-8"), media_type=media_types[resolved.suffix])
        return _serve_404()

    @app.api_route("/{page}", methods=_PUBLIC_METHODS, include_in_schema=False)
    def static_page(page: str):
        """Serve decision/comparison pages and IndexNow key from static directory."""
        if page == "fee-observatory":
            return RedirectResponse(url="/fees", status_code=308)
        if page == "mcp":
            return RedirectResponse(url="/mcp-setup", status_code=302)
        allowed = {
            "vs-mempool", "vs-blockcypher", "best-bitcoin-api-for-developers",
            "bitcoin-api-for-ai-agents", "self-hosted-bitcoin-api",
            "bitcoin-fee-api", "bitcoin-mempool-api", "bitcoin-mcp-setup-guide",
            "bitcoin-transaction-fee-calculator", "best-time-to-send-bitcoin",
            "bitcoin-fee-estimator", "bitcoin-api-for-trading-bots",
            "how-to-reduce-bitcoin-transaction-fees",
            "bitcoin-api-for-aml-compliance",
            "terms", "privacy", "disclaimer", "visualizer", "pricing", "about", "guide",
            "mcp-setup", "ai", "fees", "x402",
        }
        if page in allowed:
            p = _STATIC_DIR / f"{page}.html"
            if p.exists():
                return _render_html(p) or _serve_404()
        if page.endswith(".txt") and len(page) == 36:
            p = _STATIC_DIR / page
            if p.exists():
                return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()
