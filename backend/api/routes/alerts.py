"""Alert management routes — CRUD + trigger agent pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.agents.orchestrator import FraudDetectionOrchestrator
from backend.models.alert import Alert, AlertCreate, AlertStatus, AlertUpdate, AlertTypology

router = APIRouter()


def _get_services(request: Request):
    return request.app.state.cosmos, request.app.state.search, request.app.state.foundry


# ── List alerts ───────────────────────────────────────────────────────────────
@router.get("/", response_model=List[dict])
async def list_alerts(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    cosmos, _, _ = _get_services(request)
    return await cosmos.list_alerts(status=status, limit=limit, offset=offset)


# ── Create alert ──────────────────────────────────────────────────────────────
@router.post("/", response_model=dict, status_code=201)
async def create_alert(request: Request, body: AlertCreate):
    cosmos, _, _ = _get_services(request)
    alert_dict = body.model_dump(mode="json")
    alert_dict["id"] = str(uuid.uuid4())
    alert_dict["status"] = AlertStatus.NEW.value
    alert_dict["created_at"] = datetime.utcnow().isoformat()
    alert_dict["updated_at"] = datetime.utcnow().isoformat()
    alert_dict["is_pep"] = False
    alert_dict["is_high_value"] = (body.amount or 0) > 100_000
    alert_dict["is_swift"] = False
    saved = await cosmos.save_alert(alert_dict)
    return saved


# ── Get alert ─────────────────────────────────────────────────────────────────
@router.get("/{alert_id}", response_model=dict)
async def get_alert(request: Request, alert_id: str, account_id: str):
    cosmos, _, _ = _get_services(request)
    alert = await cosmos.get_alert(alert_id, account_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ── Update alert ──────────────────────────────────────────────────────────────
@router.patch("/{alert_id}", response_model=dict)
async def update_alert(request: Request, alert_id: str, account_id: str, body: AlertUpdate):
    cosmos, _, _ = _get_services(request)
    alert = await cosmos.get_alert(alert_id, account_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    updates = body.model_dump(exclude_none=True)
    alert.update(updates)
    alert["updated_at"] = datetime.utcnow().isoformat()
    return await cosmos.save_alert(alert)


# ── Trigger agent pipeline ────────────────────────────────────────────────────
class TriggerPipelineRequest(BaseModel):
    account_id: str
    session_id: Optional[str] = None


@router.post("/{alert_id}/investigate", response_model=dict)
async def investigate_alert(
    request: Request, alert_id: str, body: TriggerPipelineRequest
):
    """Trigger the full multi-agent fraud detection pipeline for an alert."""
    cosmos, search, foundry = _get_services(request)
    alert_dict = await cosmos.get_alert(alert_id, body.account_id)
    if not alert_dict:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Hydrate a typed Alert
    try:
        alert = Alert(**alert_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid alert data: {e}")

    orchestrator = FraudDetectionOrchestrator(cosmos, search, foundry)
    result = await orchestrator.process_alert(alert, session_id=body.session_id)
    return result.model_dump(mode="json")


# ── Get agent outputs for an alert ────────────────────────────────────────────
@router.get("/{alert_id}/agent-runs", response_model=List[dict])
async def get_agent_runs(request: Request, alert_id: str):
    cosmos, _, _ = _get_services(request)
    runs = await cosmos.get_agent_runs_for_alert(alert_id)
    # Return only specialist agent outputs (exclude orchestrator summary records)
    return [r for r in runs if r.get("agent_name")]


# ── WebSocket: real-time agent status stream ──────────────────────────────────
@router.websocket("/{alert_id}/ws")
async def alert_ws(websocket: WebSocket, alert_id: str):
    """Stream agent pipeline status updates to connected clients."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"alert_id": alert_id, "status": "connected", "echo": data})
    except WebSocketDisconnect:
        pass
