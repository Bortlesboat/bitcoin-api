"""Static file routes: landing page, robots.txt, sitemap, decision pages."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from . import __version__

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
_LANDING_PAGE = _STATIC_DIR / "index.html"


def register_static_routes(app: FastAPI):
    """Register landing page, robots.txt, sitemap, healthz, and static decision pages."""

    @app.get("/", include_in_schema=False)
    def root():
        if _LANDING_PAGE.exists():
            return HTMLResponse(_LANDING_PAGE.read_text(encoding="utf-8"))
        return {
            "name": "Satoshi API",
            "version": __version__,
            "docs": "/docs",
            "api": "/api/v1/health",
        }

    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt():
        p = _STATIC_DIR / "robots.txt"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return Response("User-agent: *\nAllow: /\n", media_type="text/plain")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml():
        p = _STATIC_DIR / "sitemap.xml"
        if p.exists():
            return Response(p.read_text(encoding="utf-8"), media_type="application/xml")
        return Response(status_code=404)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        """Process-alive check (no RPC call). Use for container healthchecks."""
        return {"status": "ok"}

    @app.get("/{page}", include_in_schema=False)
    def static_page(page: str):
        """Serve decision/comparison pages and IndexNow key from static directory."""
        allowed = {
            "vs-mempool", "vs-blockcypher", "best-bitcoin-api-for-developers",
            "bitcoin-api-for-ai-agents", "self-hosted-bitcoin-api",
            "bitcoin-fee-api", "bitcoin-mempool-api",
            "terms", "privacy",
        }
        if page in allowed:
            p = _STATIC_DIR / f"{page}.html"
            if p.exists():
                return HTMLResponse(p.read_text(encoding="utf-8"))
        if page.endswith(".txt") and len(page) == 36:
            p = _STATIC_DIR / page
            if p.exists():
                return Response(p.read_text(encoding="utf-8"), media_type="text/plain")
        return Response(status_code=404)
