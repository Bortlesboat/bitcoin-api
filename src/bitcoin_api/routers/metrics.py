"""Prometheus /metrics endpoint."""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from ..metrics import REGISTRY

router = APIRouter(tags=["Monitoring"])


@router.get(
    "/metrics",
    response_class=Response,
    summary="Prometheus metrics",
    description="Returns Prometheus text exposition format metrics for scraping.",
    responses={200: {"content": {"text/plain": {}}}},
)
async def prometheus_metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
