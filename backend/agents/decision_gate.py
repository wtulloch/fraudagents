"""
Decision Gate — deterministic, rule-based disposition of fraud/AML alerts.

Per design spec: "Final SAR/no-SAR governed by deterministic rule logic,
not LLM output." LLM generates evidence summaries; this module makes the
disposition call.

Decision tree:
  1. HITL required → PENDING_HITL (always trumps other rules)
  2. SAR threshold (≥0.75) → SAR_FILE
  3. Escalate threshold (0.50–0.74) → ESCALATE
  4. Auto-close eligible (< 0.25 + consensus) → CLOSE_NO_ACTION
  5. Default → ESCALATE (conservative fallback)
"""

from __future__ import annotations

import structlog

from backend.config import settings
from backend.models.agent_output import (
    DecisionOutcome,
    DecisionResult,
    RiskLevel,
    RiskSignal,
)
from backend.utils.hitl_manager import HITLManager

logger = structlog.get_logger(__name__)


class DecisionGate:
    def __init__(self, hitl_manager: HITLManager) -> None:
        self.hitl = hitl_manager

    def decide(
        self,
        risk_signal: RiskSignal,
        alert_metadata: dict,
    ) -> DecisionResult:
        """
        Synchronous, deterministic decision — zero LLM inference.
        Returns a DecisionResult with full rationale for audit.
        """
        score = risk_signal.composite_score
        level = risk_signal.risk_level

        # ── Rule 1: HITL override ────────────────────────────────────────────
        if risk_signal.requires_hitl:
            return DecisionResult(
                alert_id=risk_signal.alert_id,
                outcome=DecisionOutcome.PENDING_HITL,
                rationale=(
                    f"Human review required: {risk_signal.hitl_reason}. "
                    f"Composite risk score: {score:.2f} ({level})."
                ),
                rule_triggered="RULE_HITL_OVERRIDE",
                risk_score=score,
                risk_level=level,
                requires_sar=score >= settings.risk_sar_threshold,
                auto_sar_eligible=False,
            )

        # ── Rule 2: SAR threshold ────────────────────────────────────────────
        if score >= settings.risk_sar_threshold:
            auto_sar = self._auto_sar_eligible(risk_signal)
            return DecisionResult(
                alert_id=risk_signal.alert_id,
                outcome=DecisionOutcome.SAR_FILE,
                rationale=(
                    f"Composite risk score {score:.2f} exceeds SAR threshold "
                    f"({settings.risk_sar_threshold}). Risk level: {level}. "
                    f"Key flags: {', '.join(risk_signal.all_flags[:5])}."
                ),
                rule_triggered="RULE_SAR_THRESHOLD",
                risk_score=score,
                risk_level=level,
                requires_sar=True,
                auto_sar_eligible=auto_sar,
            )

        # ── Rule 3: Escalate threshold ───────────────────────────────────────
        if score >= settings.risk_escalate_threshold:
            return DecisionResult(
                alert_id=risk_signal.alert_id,
                outcome=DecisionOutcome.ESCALATE,
                rationale=(
                    f"Composite risk score {score:.2f} falls in escalation band "
                    f"({settings.risk_escalate_threshold}–{settings.risk_sar_threshold}). "
                    f"Risk level: {level}. Flags: {', '.join(risk_signal.all_flags[:3])}."
                ),
                rule_triggered="RULE_ESCALATE_THRESHOLD",
                risk_score=score,
                risk_level=level,
                requires_sar=False,
                escalation_reason=f"Score in escalation band with flags: {risk_signal.all_flags[:3]}",
            )

        # ── Rule 4: Auto-close ───────────────────────────────────────────────
        if self.hitl.auto_close_eligible(risk_signal):
            return DecisionResult(
                alert_id=risk_signal.alert_id,
                outcome=DecisionOutcome.CLOSE_NO_ACTION,
                rationale=(
                    f"Composite risk score {score:.2f} below auto-close threshold "
                    f"({settings.risk_auto_close_threshold}) with 2+ agent consensus. "
                    f"No suspicious activity indicators detected."
                ),
                rule_triggered="RULE_AUTO_CLOSE_CONSENSUS",
                risk_score=score,
                risk_level=level,
                requires_sar=False,
            )

        # ── Rule 5: Conservative fallback ────────────────────────────────────
        return DecisionResult(
            alert_id=risk_signal.alert_id,
            outcome=DecisionOutcome.ESCALATE,
            rationale=(
                f"Score {score:.2f} does not meet auto-close criteria. "
                f"Conservative escalation applied."
            ),
            rule_triggered="RULE_CONSERVATIVE_FALLBACK",
            risk_score=score,
            risk_level=level,
            requires_sar=False,
            escalation_reason="Conservative fallback — insufficient consensus for auto-close",
        )

    def _auto_sar_eligible(self, risk_signal: RiskSignal) -> bool:
        """SAR can be auto-drafted if score is high AND no HITL trigger."""
        return (
            risk_signal.composite_score >= settings.risk_sar_threshold
            and not risk_signal.requires_hitl
            and risk_signal.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )
