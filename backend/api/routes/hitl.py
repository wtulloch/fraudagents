"""HITL (Human-in-the-Loop) queue routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.utils.hitl_manager import HITLManager

router = APIRouter()


class HITLResolution(BaseModel):
    analyst_username: str
    decision: str  # "SAR_FILE" | "CLOSE" | "ESCALATE"
    notes: Optional[str] = None


@router.get("/queue")
async def get_queue(request: Request, resolved: bool = False):
    cosmos = request.app.state.cosmos
    hitl = HITLManager(cosmos)
    return await hitl.get_queue(resolved=resolved)


@router.post("/queue/{item_id}/resolve")
async def resolve_queue_item(
    request: Request, item_id: str, alert_id: str, body: HITLResolution
):
    cosmos = request.app.state.cosmos
    hitl = HITLManager(cosmos)
    result = await hitl.resolve(
        item_id=item_id,
        alert_id=alert_id,
        analyst_username=body.analyst_username,
        decision=body.decision,
        notes=body.notes,
    )
    if not result:
        raise HTTPException(status_code=404, detail="HITL queue item not found")

    # Audit the resolution
    await cosmos.log_audit({
        "id": item_id + "-resolved",
        "alert_id": alert_id,
        "event_type": "HITL_RESOLVED",
        "actor": body.analyst_username,
        "details": {"decision": body.decision, "notes": body.notes},
    })
    return result
