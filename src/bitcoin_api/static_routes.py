"""Static file routes: landing page, robots.txt, sitemap, decision pages, admin dashboard."""

import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from . import __version__

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
_LANDING_PAGE = _STATIC_DIR / "index.html"
_404_PAGE = _STATIC_DIR / "404.html"
_HISTORY_DIR = _STATIC_DIR / "history"
_HISTORY_PAGES = {"index", "block", "tx", "address"}


def _serve_404():
    """Return branded 404 page with PostHog key injected."""
    if _404_PAGE.exists():
        from .config import settings
        html = _404_PAGE.read_text(encoding="utf-8")
        ph_key = settings.posthog_api_key.get_secret_value() if settings.posthog_api_key else ""
        html = html.replace("__POSTHOG_API_KEY__", ph_key)
        return HTMLResponse(html, status_code=404)
    return Response(status_code=404)


def register_static_routes(app: FastAPI):
    """Register landing page, robots.txt, sitemap, healthz, and static decision pages."""

    @app.get("/", include_in_schema=False)
    def root():
        if _LANDING_PAGE.exists():
            from .config import settings
            html = _LANDING_PAGE.read_text(encoding="utf-8")
            ph_key = settings.posthog_api_key.get_secret_value() if settings.posthog_api_key else ""
            html = html.replace("__POSTHOG_API_KEY__", ph_key)
            return HTMLResponse(html)
        return {
            "name": "Satoshi API",
            "version": __version__,
            "docs": "/docs",
            "api": "/api/v1/health",
        }

    @app.get("/.well-known/mcp/server-card.json", include_in_schema=False)
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

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        p = _STATIC_DIR / "favicon.ico"
        if p.exists():
            return Response(p.read_bytes(), media_type="image/x-icon")
        return Response(status_code=204)

    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt():
        p = _STATIC_DIR / "robots.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return Response("User-agent: *\nAllow: /\n", media_type="text/plain")

    @app.get("/llms.txt", include_in_schema=False)
    def llms_txt():
        p = _STATIC_DIR / "llms.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()

    @app.get("/llms-full.txt", include_in_schema=False)
    def llms_full_txt():
        p = _STATIC_DIR / "llms-full.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml():
        p = _STATIC_DIR / "sitemap.xml"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="application/xml")
        return _serve_404()

    _IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp"}

    @app.get("/{filename}.{ext}", include_in_schema=False)
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

    @app.get("/admin/dashboard", include_in_schema=False)
    def admin_dashboard(key: str = Query("")):
        """Admin analytics dashboard — requires admin key via ?key= query param."""
        from .config import settings
        if not settings.admin_api_key:
            raise HTTPException(status_code=403, detail="Admin not configured")
        if not key or not secrets.compare_digest(key, settings.admin_api_key.get_secret_value()):
            raise HTTPException(status_code=403, detail="Invalid admin key")
        p = _STATIC_DIR / "admin-dashboard.html"
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
        return _serve_404()

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        """Process-alive check (no RPC call). Use for container healthchecks."""
        return {"status": "ok"}

    @app.get("/history", include_in_schema=False)
    def history_index():
        """Serve the History Explorer index page (feature-flag gated)."""
        from .config import settings
        if not settings.enable_history_explorer:
            return _serve_404()
        p = _HISTORY_DIR / "index.html"
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
        return _serve_404()

    @app.get("/history/{page}", include_in_schema=False)
    def history_page(page: str):
        """Serve History Explorer sub-pages and static assets."""
        from .config import settings
        if not settings.enable_history_explorer:
            return _serve_404()
        # Known HTML pages
        if page in _HISTORY_PAGES:
            p = _HISTORY_DIR / f"{page}.html"
            if p.exists():
                return HTMLResponse(p.read_text(encoding="utf-8"))
            return _serve_404()
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

    @app.get("/{page}", include_in_schema=False)
    def static_page(page: str):
        """Serve decision/comparison pages and IndexNow key from static directory."""
        allowed = {
            "vs-mempool", "vs-blockcypher", "best-bitcoin-api-for-developers",
            "bitcoin-api-for-ai-agents", "self-hosted-bitcoin-api",
            "bitcoin-fee-api", "bitcoin-mempool-api", "bitcoin-mcp-setup-guide",
            "terms", "privacy", "disclaimer", "visualizer", "pricing", "about", "guide",
        }
        if page in allowed:
            p = _STATIC_DIR / f"{page}.html"
            if p.exists():
                from .config import settings
                html = p.read_text(encoding="utf-8")
                ph_key = settings.posthog_api_key.get_secret_value() if settings.posthog_api_key else ""
                html = html.replace("__POSTHOG_API_KEY__", ph_key)
                return HTMLResponse(html)
        if page.endswith(".txt") and len(page) == 36:
            p = _STATIC_DIR / page
            if p.exists():
                return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return _serve_404()
