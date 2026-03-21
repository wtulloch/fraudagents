"""
Main Fraud Detection Orchestrator — fan-out / fan-in pattern using asyncio.

Flow:
  1. AlertRouter enriches context and determines which agents to run
  2. Fan-out: all specialist agents execute in parallel (asyncio.gather)
  3. RiskAggregator combines scores with weighted, confidence-adjusted fusion
  4. DecisionGate applies deterministic rules
  5. HITL queue populated if required
  6. Full result persisted to Cosmos DB with audit trail
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

import structlog

from backend.agents.alert_router import AlertRouter
from backend.agents.decision_gate import DecisionGate
from backend.agents.risk_aggregator import RiskAggregator
from backend.agents.specialist.adverse_media_agent import AdverseMediaAgent
from backend.agents.specialist.transaction_pattern_agent import TransactionPatternAgent
from backend.agents.specialist.kyc_kyb_agent import KYCKYBAgent
from backend.agents.specialist.sanctions_agent import SanctionsAgent
from backend.agents.specialist.fraud_agent import FraudAgent
from backend.agents.specialist.aml_agent import AMLAgent
from backend.models.alert import Alert
from backend.models.agent_output import AgentOutput, OrchestratorResult
from backend.utils.audit_logger import AuditLogger
from backend.utils.hitl_manager import HITLManager

logger = structlog.get_logger(__name__)


class FraudDetectionOrchestrator:
    def __init__(
        self,
        cosmos_service,
        search_service,
        foundry_service,
    ) -> None:
        self.cosmos = cosmos_service
        self.search = search_service
        self.foundry = foundry_service

        self.hitl = HITLManager(cosmos_service)
        self.audit = AuditLogger(cosmos_service)

        self.alert_router = AlertRouter(cosmos_service)
        self.risk_aggregator = RiskAggregator(cosmos_service, self.hitl)
        self.decision_gate = DecisionGate(self.hitl)

        # Specialist agents
        self._agents: Dict[str, Any] = {
            "adverse-media-agent": AdverseMediaAgent(foundry_service, search_service),
            "transaction-pattern-agent": TransactionPatternAgent(foundry_service, search_service),
            "kyc-kyb-agent": KYCKYBAgent(foundry_service, search_service),
            "sanctions-matching-agent": SanctionsAgent(foundry_service, search_service),
            "fraud-agent": FraudAgent(foundry_service, search_service),
            "aml-agent": AMLAgent(foundry_service, search_service),
        }

    async def process_alert(
        self, alert: Alert, session_id: Optional[str] = None
    ) -> OrchestratorResult:
        """
        End-to-end pipeline: route → fan-out → fan-in → decide → audit.
        """
        t0 = time.monotonic()
        logger.info("pipeline_start", alert_id=alert.id, typology=alert.typology)

        # ── Step 1: Route alert ────────────────────────────────────────────
        context = await self.alert_router.route(alert)
        agents_to_invoke = context["agents_to_invoke"]

        await self.audit.log_alert_created(
            alert_id=alert.id,
            source=alert.source.value,
            details={"typology": alert.typology, "agents": agents_to_invoke},
        )

        # ── Step 2: Fan-out — parallel agent execution ─────────────────────
        tasks = [
            self._run_agent_safe(agent_name, alert, context)
            for agent_name in agents_to_invoke
            if agent_name in self._agents
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=False)
        agent_outputs: List[AgentOutput] = raw_results

        # Persist agent runs
        for output in agent_outputs:
            await self.cosmos.save_agent_run(output.model_dump(mode="json"))
            await self.audit.log_agent_run(
                alert_id=alert.id,
                agent_name=output.agent_name.value,
                run_id=output.run_id,
                risk_score=output.risk_score,
                flags=output.flags,
                citations=[c["source"] for c in (output.citations or [])],
                latency_ms=output.latency_ms or 0,
            )

        # ── Step 3: Fan-in — risk aggregation ──────────────────────────────
        await self.risk_aggregator.load_feedback_weights()
        risk_signal = await self.risk_aggregator.aggregate(
            agent_outputs, alert_metadata=alert.model_dump(mode="json")
        )

        # ── Step 4: Deterministic Decision Gate ───────────────────────────
        decision = self.decision_gate.decide(risk_signal, alert.model_dump(mode="json"))

        await self.audit.log_decision(
            alert_id=alert.id,
            outcome=decision.outcome.value,
            rule_triggered=decision.rule_triggered,
            risk_score=decision.risk_score,
            rationale=decision.rationale,
        )

        # ── Step 5: HITL queue ─────────────────────────────────────────────
        if risk_signal.requires_hitl:
            await self.hitl.enqueue(
                alert_id=alert.id,
                case_id=None,
                reason=risk_signal.hitl_reason or "Human review required",
                risk_signal=risk_signal.model_dump(exclude={"agent_outputs"}),
                priority="HIGH" if decision.requires_sar else "MEDIUM",
            )
            await self.audit.log_hitl_required(alert.id, risk_signal.hitl_reason or "")

        # ── Step 6: Update alert status in Cosmos ─────────────────────────
        alert_dict = alert.model_dump(mode="json")
        alert_dict["status"] = self._outcome_to_status(decision.outcome.value)
        alert_dict["risk_score"] = decision.risk_score
        await self.cosmos.save_alert(alert_dict)

        total_ms = int((time.monotonic() - t0) * 1000)

        result = OrchestratorResult(
            alert_id=alert.id,
            agent_outputs=agent_outputs,
            risk_signal=risk_signal,
            decision=decision,
            total_latency_ms=total_ms,
        )

        # Persist full orchestrator result
        await self.cosmos.save_agent_run({
            "id": str(uuid.uuid4()),
            "alert_id": alert.id,
            "type": "orchestrator_result",
            "result": result.model_dump(mode="json"),
        })

        logger.info(
            "pipeline_complete",
            alert_id=alert.id,
            outcome=decision.outcome,
            risk_score=decision.risk_score,
            total_ms=total_ms,
        )
        return result

    async def _run_agent_safe(
        self, agent_name: str, alert: Alert, context: Dict[str, Any]
    ) -> AgentOutput:
        """Execute a single specialist agent; return error output on failure."""
        agent = self._agents[agent_name]
        try:
            return await agent.analyze(alert, context)
        except Exception as e:
            logger.error("agent_run_failed", agent=agent_name, alert_id=alert.id, error=str(e))
            from backend.models.agent_output import AgentName, RiskLevel
            return AgentOutput(
                agent_name=AgentName(agent_name.replace("-agent", "").replace("-", "_")),
                alert_id=alert.id,
                run_id=str(uuid.uuid4()),
                model_used="n/a",
                finding=f"Agent failed: {str(e)[:200]}",
                risk_score=0.5,  # neutral fallback — avoid false comfort
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                error=str(e),
            )

    def _outcome_to_status(self, outcome: str) -> str:
        mapping = {
            "SAR_FILE": "SAR_DRAFT",
            "ESCALATE": "ESCALATED",
            "CLOSE_NO_ACTION": "CLOSED_NO_ACTION",
            "PENDING_HITL": "PENDING_HITL",
        }
        return mapping.get(outcome, "IN_INVESTIGATION")
