"""Case management routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request

from backend.models.case import Case, CaseCreate, CaseNote, CaseStatus, CaseTier

router = APIRouter()


def _cosmos(request: Request):
    return request.app.state.cosmos


@router.get("/", response_model=List[dict])
async def list_cases(request: Request, status: Optional[str] = None, limit: int = 50):
    q = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
    params = [{"name": "@limit", "value": limit}]
    if status:
        q = "SELECT * FROM c WHERE c.status = @status ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        params.append({"name": "@status", "value": status})
    return await _cosmos(request).query("cases", q, params)


@router.post("/", response_model=dict, status_code=201)
async def create_case(request: Request, body: CaseCreate):
    cosmos = _cosmos(request)
    case_dict = body.model_dump(mode="json")
    case_dict["id"] = str(uuid.uuid4())
    case_dict["status"] = CaseStatus.OPEN.value
    case_dict["created_at"] = datetime.utcnow().isoformat()
    case_dict["updated_at"] = datetime.utcnow().isoformat()
    case_dict["risk_score"] = 0.0
    case_dict["evidence_package"] = []
    case_dict["notes"] = []
    return await cosmos.save_case(case_dict)


@router.get("/{case_id}", response_model=dict)
async def get_case(request: Request, case_id: str, account_id: str):
    cosmos = _cosmos(request)
    case = await cosmos.get_case(case_id, account_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/{case_id}/notes", response_model=dict)
async def add_note(request: Request, case_id: str, account_id: str, body: CaseNote):
    cosmos = _cosmos(request)
    case = await cosmos.get_case(case_id, account_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    note = body.model_dump()
    case["notes"].append(note)
    case["updated_at"] = datetime.utcnow().isoformat()
    return await cosmos.save_case(case)


@router.patch("/{case_id}/status", response_model=dict)
async def update_case_status(
    request: Request, case_id: str, account_id: str, status: str
):
    cosmos = _cosmos(request)
    case = await cosmos.get_case(case_id, account_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case["status"] = status
    case["updated_at"] = datetime.utcnow().isoformat()
    if status == CaseStatus.CLOSED.value:
        case["closed_at"] = datetime.utcnow().isoformat()
    return await cosmos.save_case(case)
