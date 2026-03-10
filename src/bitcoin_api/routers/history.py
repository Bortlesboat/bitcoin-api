"""History Explorer — curated Bitcoin history + on-chain exploration.

Siloed feature: controlled by ENABLE_HISTORY_EXPLORER env var.
All routes live under /api/v1/history/ and static pages under /history/.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger("bitcoin_api.history")

router = APIRouter(prefix="/history", tags=["History Explorer"])

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static" / "history"
_DATA_FILE = _STATIC_DIR / "history-data.json"

_history_data: dict | None = None


def _load_data() -> dict:
    global _history_data
    if _history_data is None:
        if _DATA_FILE.exists():
            _history_data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        else:
            _history_data = {"eras": [], "events": []}
            log.warning("History data file not found: %s", _DATA_FILE)
    return _history_data


@router.get("/events")
def list_events(
    era: str | None = Query(None, description="Filter by era ID"),
    category: str | None = Query(None, description="Filter by category"),
    tag: str | None = Query(None, description="Filter by tag"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = _load_data()
    events = data.get("events", [])
    if era:
        events = [e for e in events if e.get("era") == era]
    if category:
        events = [e for e in events if e.get("category") == category]
    if tag:
        events = [e for e in events if tag in e.get("tags", [])]
    total = len(events)
    events = events[offset : offset + limit]
    return {"data": events, "meta": {"total": total, "offset": offset, "limit": limit}}


@router.get("/events/{event_id}")
def get_event(event_id: str):
    data = _load_data()
    for event in data.get("events", []):
        if event.get("id") == event_id:
            return {"data": event}
    raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")


@router.get("/eras")
def list_eras():
    data = _load_data()
    return {"data": data.get("eras", [])}


@router.get("/eras/{era_id}")
def get_era(era_id: str):
    data = _load_data()
    for era in data.get("eras", []):
        if era.get("id") == era_id:
            return {"data": era}
    raise HTTPException(status_code=404, detail=f"Era '{era_id}' not found")


@router.get("/concepts")
def list_concepts():
    data = _load_data()
    return {"data": data.get("concepts", {})}


@router.get("/concepts/{concept_id}")
def get_concept(concept_id: str):
    data = _load_data()
    concepts = data.get("concepts", {})
    if concept_id not in concepts:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    return {"data": {**concepts[concept_id], "id": concept_id}}


@router.get("/search")
def search_history(q: str = Query(..., min_length=1, description="Search query")):
    data = _load_data()
    q_lower = q.lower()
    results = []
    for event in data.get("events", []):
        score = 0
        if q_lower in event.get("title", "").lower():
            score += 3
        if q_lower in event.get("description", "").lower():
            score += 1
        if any(q_lower in tag for tag in event.get("tags", [])):
            score += 2
        if score > 0:
            results.append({"event": event, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"data": [r["event"] for r in results[:20]], "meta": {"query": q, "total": len(results)}}
