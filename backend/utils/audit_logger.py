"""
Full audit trail — every agent step, decision, and user action is logged
to Cosmos DB with data sources, reasoning, and decision rationale.

Satisfies SR 11-7 compliance logging requirements.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class AuditLogger:
    def __init__(self, cosmos_service) -> None:
        self.cosmos = cosmos_service

    async def log(
        self,
        event_type: str,
        alert_id: Optional[str],
        actor: str,
        details: Dict[str, Any],
        data_sources: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "alert_id": alert_id or "SYSTEM",
            "event_type": event_type,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
            "data_sources": data_sources or [],
            "reasoning": reasoning or "",
            "outcome": outcome or "",
        }
        await self.cosmos.log_audit(event)
        logger.info(
            "audit_event",
            event_type=event_type,
            alert_id=alert_id,
            actor=actor,
            outcome=outcome,
        )
        return event_id

    # ── Convenience wrappers ──────────────────────────────────────────────────

    async def log_alert_created(self, alert_id: str, source: str, details: Dict[str, Any]) -> str:
        return await self.log(
            event_type="ALERT_CREATED",
            alert_id=alert_id,
            actor=source,
            details=details,
            outcome="ALERT_QUEUED",
        )

    async def log_agent_run(
        self,
        alert_id: str,
        agent_name: str,
        run_id: str,
        risk_score: float,
        flags: List[str],
        citations: List[str],
        latency_ms: int,
    ) -> str:
        return await self.log(
            event_type="AGENT_RUN_COMPLETED",
            alert_id=alert_id,
            actor=agent_name,
            details={
                "run_id": run_id,
                "risk_score": risk_score,
                "flags": flags,
                "latency_ms": latency_ms,
            },
            data_sources=citations,
            outcome=f"RISK_SCORE_{risk_score:.2f}",
        )

    async def log_decision(
        self,
        alert_id: str,
        outcome: str,
        rule_triggered: str,
        risk_score: float,
        rationale: str,
    ) -> str:
        return await self.log(
            event_type="DECISION_MADE",
            alert_id=alert_id,
            actor="DECISION_GATE",
            details={
                "outcome": outcome,
                "rule_triggered": rule_triggered,
                "risk_score": risk_score,
            },
            reasoning=rationale,
            outcome=outcome,
        )

    async def log_hitl_required(self, alert_id: str, reason: str) -> str:
        return await self.log(
            event_type="HITL_REQUIRED",
            alert_id=alert_id,
            actor="ORCHESTRATOR",
            details={"reason": reason},
            outcome="PENDING_HUMAN_REVIEW",
        )

    async def log_hitl_resolved(
        self, alert_id: str, analyst: str, resolution: str, notes: str
    ) -> str:
        return await self.log(
            event_type="HITL_RESOLVED",
            alert_id=alert_id,
            actor=analyst,
            details={"resolution": resolution, "notes": notes},
            outcome=resolution,
        )

    async def log_sar_event(
        self, alert_id: str, sar_id: str, event: str, actor: str
    ) -> str:
        return await self.log(
            event_type=f"SAR_{event}",
            alert_id=alert_id,
            actor=actor,
            details={"sar_id": sar_id},
            outcome=f"SAR_{event}",
        )

    async def log_feedback(
        self, alert_id: str, analyst: str, agent_name: str, correct: bool
    ) -> str:
        return await self.log(
            event_type="FEEDBACK_SUBMITTED",
            alert_id=alert_id,
            actor=analyst,
            details={"agent_name": agent_name, "marked_correct": correct},
            outcome="FEEDBACK_RECORDED",
        )
