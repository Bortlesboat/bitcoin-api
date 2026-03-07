"""Prometheus /metrics endpoint — admin-only."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from ..metrics import REGISTRY

router = APIRouter(tags=["Monitoring"])


def _require_admin(request: Request):
    from ..config import settings
    if not settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Metrics not configured")
    key = request.headers.get("X-Admin-Key", "")
    if not secrets.compare_digest(key, settings.admin_api_key):
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.get(
    "/metrics",
    response_class=Response,
    summary="Prometheus metrics",
    description="Returns Prometheus text exposition format metrics for scraping. Requires X-Admin-Key header.",
    responses={200: {"content": {"text/plain": {}}}},
    dependencies=[Depends(_require_admin)],
)
async def prometheus_metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
