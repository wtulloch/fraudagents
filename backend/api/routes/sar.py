"""SAR drafting, review, and filing routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request

from backend.models.sar import SAR, SARApproval, SARDraftRequest, SARStatus
from backend.services.foundry_service import FoundryService

router = APIRouter()


def _services(request: Request):
    return request.app.state.cosmos, request.app.state.foundry


@router.get("/", response_model=List[dict])
async def list_sars(request: Request, status: Optional[str] = None):
    cosmos, _ = _services(request)
    return await cosmos.list_sars(status=status)


@router.post("/draft", response_model=dict, status_code=201)
async def draft_sar(request: Request, body: SARDraftRequest):
    """Auto-draft a SAR narrative using the SAR Drafting Agent."""
    cosmos, foundry = _services(request)

    # Gather evidence from agent runs
    all_runs = []
    for alert_id in body.alert_ids:
        runs = await cosmos.get_agent_runs_for_alert(alert_id)
        all_runs.extend(runs)

    evidence_summary = "\n".join(
        f"- [{r.get('agent_name', 'agent')}]: {r.get('finding', '')[:200]}"
        for r in all_runs
        if r.get("finding")
    )

    prompt = (
        f"Draft a FinCEN Form 111 SAR narrative for case {body.case_id}.\n\n"
        f"Evidence summary from specialist agents:\n{evidence_summary}\n\n"
        f"Additional context: {body.additional_context or 'None'}\n\n"
        "Return a JSON object matching the SARNarrative schema with all relevant fields populated."
    )

    try:
        result = await foundry.run_agent("sar-drafting-agent", prompt)
        narrative_text = result.get("response_text", "")
    except Exception as e:
        narrative_text = f"Draft narrative placeholder. Error: {str(e)[:200]}"

    sar_dict = {
        "id": str(uuid.uuid4()),
        "case_id": body.case_id,
        "alert_ids": body.alert_ids,
        "status": SARStatus.DRAFT.value,
        "filing_type": body.filing_type.value,
        "narrative": {
            "narrative_text": narrative_text,
            "drafted_by_agent": True,
            "agent_confidence": 0.75,
            "transaction_ids": [],
        },
        "drafted_at": datetime.utcnow().isoformat(),
        "revision_history": [],
    }

    await cosmos.log_audit({
        "id": str(uuid.uuid4()),
        "alert_id": body.alert_ids[0] if body.alert_ids else "unknown",
        "event_type": "SAR_DRAFTED",
        "actor": "sar-drafting-agent",
        "details": {"sar_id": sar_dict["id"], "case_id": body.case_id},
    })

    return await cosmos.save_sar(sar_dict)


@router.get("/{sar_id}", response_model=dict)
async def get_sar(request: Request, sar_id: str, case_id: str):
    cosmos, _ = _services(request)
    sar = await cosmos.get_sar(sar_id, case_id)
    if not sar:
        raise HTTPException(status_code=404, detail="SAR not found")
    return sar


@router.post("/{sar_id}/approve", response_model=dict)
async def approve_sar(request: Request, sar_id: str, case_id: str, body: SARApproval):
    """Compliance officer approves or rejects a SAR draft."""
    cosmos, _ = _services(request)
    sar = await cosmos.get_sar(sar_id, case_id)
    if not sar:
        raise HTTPException(status_code=404, detail="SAR not found")

    sar["reviewer_username"] = body.reviewer_username
    if body.approved:
        sar["status"] = SARStatus.APPROVED.value
        sar["compliance_reviewed_at"] = datetime.utcnow().isoformat()
    else:
        sar["status"] = SARStatus.REJECTED.value

    sar["revision_history"].append({
        "action": "APPROVED" if body.approved else "REJECTED",
        "by": body.reviewer_username,
        "comments": body.comments,
        "timestamp": datetime.utcnow().isoformat(),
    })

    await cosmos.log_audit({
        "id": str(uuid.uuid4()),
        "alert_id": sar.get("alert_ids", ["unknown"])[0],
        "event_type": "SAR_APPROVED" if body.approved else "SAR_REJECTED",
        "actor": body.reviewer_username,
        "details": {"sar_id": sar_id},
    })

    return await cosmos.save_sar(sar)


@router.post("/{sar_id}/file", response_model=dict)
async def file_sar(request: Request, sar_id: str, case_id: str, filed_by: str):
    """Mark SAR as filed with FinCEN (placeholder — real implementation needs BSA e-filing)."""
    cosmos, _ = _services(request)
    sar = await cosmos.get_sar(sar_id, case_id)
    if not sar:
        raise HTTPException(status_code=404, detail="SAR not found")
    if sar.get("status") != SARStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="SAR must be approved before filing")

    sar["status"] = SARStatus.FILED.value
    sar["filed_at"] = datetime.utcnow().isoformat()
    sar["fincen_confirmation_number"] = f"FINCEN-{uuid.uuid4().hex[:12].upper()}"

    await cosmos.log_audit({
        "id": str(uuid.uuid4()),
        "alert_id": sar.get("alert_ids", ["unknown"])[0],
        "event_type": "SAR_FILED",
        "actor": filed_by,
        "details": {"sar_id": sar_id, "confirmation": sar["fincen_confirmation_number"]},
    })

    return await cosmos.save_sar(sar)
