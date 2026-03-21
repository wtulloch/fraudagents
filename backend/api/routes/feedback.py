"""Feedback / Reinforcement Learning routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.utils.feedback_processor import FeedbackProcessor

router = APIRouter()


class FeedbackSubmission(BaseModel):
    alert_id: str
    agent_name: str
    run_id: str
    analyst_username: str
    is_correct: bool
    actual_risk_score: Optional[float] = None
    actual_typology: Optional[str] = None
    notes: Optional[str] = None


@router.post("/submit")
async def submit_feedback(request: Request, body: FeedbackSubmission):
    cosmos = request.app.state.cosmos
    processor = FeedbackProcessor(cosmos)
    feedback_id = await processor.submit(
        alert_id=body.alert_id,
        agent_name=body.agent_name,
        run_id=body.run_id,
        analyst_username=body.analyst_username,
        is_correct=body.is_correct,
        actual_risk_score=body.actual_risk_score,
        actual_typology=body.actual_typology,
        notes=body.notes,
    )
    return {"feedback_id": feedback_id, "recorded": True}


@router.get("/metrics")
async def get_all_metrics(request: Request):
    cosmos = request.app.state.cosmos
    processor = FeedbackProcessor(cosmos)
    return await processor.get_all_agent_metrics()


@router.get("/metrics/{agent_name}")
async def get_agent_metrics(request: Request, agent_name: str):
    cosmos = request.app.state.cosmos
    processor = FeedbackProcessor(cosmos)
    return await processor.get_agent_metrics(agent_name)


@router.get("/fine-tune-dataset/{agent_name}")
async def get_fine_tune_dataset(request: Request, agent_name: str):
    cosmos = request.app.state.cosmos
    processor = FeedbackProcessor(cosmos)
    dataset = await processor.build_fine_tune_dataset(agent_name)
    return {"agent_name": agent_name, "samples": len(dataset), "dataset": dataset}
