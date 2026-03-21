"""
Risk Aggregator — fan-in component that combines specialist agent outputs
into a single unified risk signal with feature attribution.

Weighting strategy:
  • Base: equal weighting across agents
  • Adjusted: feedback-driven per-agent weights (online RL)
  • Confidence-scaled: lower-confidence outputs contribute less
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from backend.config import settings
from backend.models.agent_output import AgentOutput, AgentName, RiskLevel, RiskSignal
from backend.utils.hitl_manager import HITLManager

logger = structlog.get_logger(__name__)

# Default agent weights (adjusted by RL feedback loop over time)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "adverse-media-agent": 0.15,
    "transaction-pattern-agent": 0.25,
    "kyc-kyb-agent": 0.20,
    "sanctions-matching-agent": 0.20,
    "fraud-agent": 0.10,
    "aml-agent": 0.10,
}

# Flag severity multipliers (for composite score adjustment)
HIGH_SEVERITY_FLAGS = {
    "OFAC_HIT", "SANCTIONS_MATCH", "PEP_MATCH", "STRUCTURING",
    "LAYERING", "ACCOUNT_TAKEOVER", "HIGH_RISK_JURISDICTION",
}


class RiskAggregator:
    def __init__(self, cosmos_service, hitl_manager: HITLManager) -> None:
        self.cosmos = cosmos_service
        self.hitl = hitl_manager
        self._weights: Dict[str, float] = dict(DEFAULT_WEIGHTS)

    async def load_feedback_weights(self) -> None:
        """Adjust agent weights based on feedback accuracy metrics."""
        try:
            # GROUP BY + AVG aggregates are unsupported by the Python SDK gateway path.
            # Fetch raw feedback rows and aggregate in Python.
            rows = await self.cosmos.query(
                "feedback",
                "SELECT c.agent_name, c.is_correct FROM c",
                [],
            )
            # Aggregate per agent
            totals: Dict[str, int] = {}
            correct: Dict[str, int] = {}
            for row in rows:
                agent = row.get("agent_name")
                if not agent:
                    continue
                totals[agent] = totals.get(agent, 0) + 1
                if row.get("is_correct"):
                    correct[agent] = correct.get(agent, 0) + 1

            for agent, count in totals.items():
                accuracy = correct.get(agent, 0) / count if count > 0 else 0.5
                if agent in self._weights and count >= 10:
                    # Blend feedback accuracy with default weight
                    base = DEFAULT_WEIGHTS.get(agent, 0.15)
                    self._weights[agent] = round(
                        0.6 * base + 0.4 * (base * (accuracy / 0.75)), 4
                    )
        except Exception as e:
            logger.warning("weight_load_failed", error=str(e))

    def _score_to_level(self, score: float) -> RiskLevel:
        if score >= 0.80:
            return RiskLevel.CRITICAL
        if score >= 0.60:
            return RiskLevel.HIGH
        if score >= 0.35:
            return RiskLevel.MEDIUM
        if score >= 0.15:
            return RiskLevel.LOW
        return RiskLevel.NEGLIGIBLE

    async def aggregate(
        self,
        agent_outputs: List[AgentOutput],
        alert_metadata: Optional[Dict[str, Any]] = None,
    ) -> RiskSignal:
        """
        Compute weighted composite risk score with flag severity boost.
        """
        if not agent_outputs:
            return RiskSignal(
                alert_id="unknown",
                composite_score=0.0,
                risk_level=RiskLevel.NEGLIGIBLE,
            )

        alert_id = agent_outputs[0].alert_id
        agent_scores: Dict[str, float] = {}
        all_flags: List[str] = []
        dominant_typologies: List[str] = []
        total_weight = 0.0
        weighted_sum = 0.0

        for output in agent_outputs:
            if output.error:
                continue  # skip failed agent runs
            agent_key = output.agent_name.value
            w = self._weights.get(agent_key, 0.15)

            # Confidence-scale the weight
            effective_weight = w * output.confidence
            weighted_sum += output.risk_score * effective_weight
            total_weight += effective_weight
            agent_scores[agent_key] = output.risk_score
            all_flags.extend(output.flags)

        composite = (weighted_sum / total_weight) if total_weight > 0 else 0.0

        # Severity boost for critical flags
        critical_flags_found = set(all_flags) & HIGH_SEVERITY_FLAGS
        if critical_flags_found:
            boost = min(0.15 * len(critical_flags_found), 0.20)
            composite = min(composite + boost, 1.0)

        all_flags_dedup = list(dict.fromkeys(all_flags))  # deduplicate, preserve order

        # Determine HITL requirement
        requires_hitl = False
        hitl_reason: Optional[str] = None
        if alert_metadata:
            # Construct a temporary RiskSignal for HITL check
            temp_signal = RiskSignal(
                alert_id=alert_id,
                composite_score=composite,
                risk_level=self._score_to_level(composite),
                agent_scores=agent_scores,
                all_flags=all_flags_dedup,
            )
            requires_hitl, hitl_reason = self.hitl.requires_hitl(temp_signal, alert_metadata)

        signal = RiskSignal(
            alert_id=alert_id,
            composite_score=round(composite, 4),
            risk_level=self._score_to_level(composite),
            agent_scores=agent_scores,
            dominant_typologies=dominant_typologies,
            all_flags=all_flags_dedup,
            requires_hitl=requires_hitl,
            hitl_reason=hitl_reason,
            agent_outputs=agent_outputs,
        )

        logger.info(
            "risk_aggregated",
            alert_id=alert_id,
            composite=composite,
            level=signal.risk_level,
            flags=all_flags_dedup[:5],
            hitl=requires_hitl,
        )
        return signal
