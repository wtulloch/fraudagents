"""Dashboard metrics route."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.services.model_router import model_router

router = APIRouter()


@router.get("/metrics")
async def get_metrics(request: Request):
    cosmos = request.app.state.cosmos
    metrics = await cosmos.get_dashboard_metrics()
    metrics["model_router"] = model_router.all_routes()
    return metrics


@router.get("/audit-trail")
async def recent_audit(request: Request, limit: int = 50):
    cosmos = request.app.state.cosmos
    q = "SELECT * FROM c ORDER BY c.logged_at DESC OFFSET 0 LIMIT @limit"
    return await cosmos.query("audit_logs", q, [{"name": "@limit", "value": limit}])
