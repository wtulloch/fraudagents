"""
Human-In-The-Loop (HITL) Manager.

Hard-wired HITL checkpoints (per design spec):
  • PEP-linked accounts (risk_score > pep_threshold)
  • High-value accounts (transaction > high_value_amount)
  • SWIFT transactions (always)
  • SAR filing (Tier 3 — always requires human sign-off)

HITL queue is persisted in Cosmos DB 'hitl_queue' container.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from backend.config import settings
from backend.models.agent_output import RiskSignal

logger = structlog.get_logger(__name__)

HITL_TRIGGERS = {
    "PEP_FLAG": "Alert involves a Politically Exposed Person",
    "HIGH_VALUE": f"Transaction exceeds ${settings.hitl_high_value_amount:,.0f}",
    "SWIFT_TRANSACTION": "Alert involves a SWIFT international wire",
    "SAR_REQUIRED": "SAR filing requires compliance officer sign-off",
    "SANCTIONS_MATCH": "Potential sanctions list match detected",
    "AGENT_CONSENSUS_MISSING": "Insufficient agent consensus for auto-close",
    "NOVEL_PATTERN": "Complex/novel fraud pattern requires human judgement",
    "TIER_3": "Tier 3 case — human sign-off always required",
}


class HITLManager:
    def __init__(self, cosmos_service) -> None:
        self.cosmos = cosmos_service

    # ── Evaluation ────────────────────────────────────────────────────────────

    def requires_hitl(
        self,
        risk_signal: RiskSignal,
        alert_metadata: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Deterministic check — returns (requires_hitl, reason).
        No LLM inference. Must be synchronous (called in Decision Gate).
        """
        flags_set = set(risk_signal.all_flags)

        if alert_metadata.get("is_pep") and risk_signal.composite_score > settings.hitl_pep_threshold:
            return True, HITL_TRIGGERS["PEP_FLAG"]

        if alert_metadata.get("is_swift") and settings.hitl_swift_require_review:
            return True, HITL_TRIGGERS["SWIFT_TRANSACTION"]

        amount = alert_metadata.get("amount", 0) or 0
        if amount > settings.hitl_high_value_amount:
            return True, HITL_TRIGGERS["HIGH_VALUE"]

        if "SANCTIONS_MATCH" in flags_set or "OFAC_HIT" in flags_set:
            return True, HITL_TRIGGERS["SANCTIONS_MATCH"]

        if risk_signal.composite_score >= settings.risk_sar_threshold:
            return True, HITL_TRIGGERS["SAR_REQUIRED"]

        return False, None

    def auto_close_eligible(self, risk_signal: RiskSignal) -> bool:
        """
        Auto-close requires composite score < threshold AND 2+ agent consensus.
        Per design spec: auto-close requires consensus from 2+ agents.
        """
        if risk_signal.composite_score > settings.risk_auto_close_threshold:
            return False
        # Count how many agents scored below auto-close threshold
        low_risk_agents = sum(
            1 for score in risk_signal.agent_scores.values()
            if score <= settings.risk_auto_close_threshold
        )
        return low_risk_agents >= 2

    # ── Queue operations ──────────────────────────────────────────────────────

    async def enqueue(
        self,
        alert_id: str,
        case_id: Optional[str],
        reason: str,
        risk_signal: Dict[str, Any],
        priority: str = "HIGH",
    ) -> str:
        item = {
            "id": f"hitl-{alert_id}",
            "alert_id": alert_id,
            "case_id": case_id,
            "reason": reason,
            "priority": priority,
            "risk_signal": risk_signal,
            "resolved": False,
        }
        result = await self.cosmos.enqueue_hitl(item)
        logger.info("hitl_enqueued", alert_id=alert_id, reason=reason)
        return result["id"]

    async def get_queue(self, resolved: bool = False) -> List[Dict[str, Any]]:
        return await self.cosmos.list_hitl_queue(resolved=resolved)

    async def resolve(
        self,
        item_id: str,
        alert_id: str,
        analyst_username: str,
        decision: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolution = {
            "analyst": analyst_username,
            "decision": decision,  # "SAR_FILE" | "CLOSE" | "ESCALATE"
            "notes": notes or "",
        }
        result = await self.cosmos.resolve_hitl(item_id, alert_id, resolution)
        logger.info("hitl_resolved", item_id=item_id, analyst=analyst_username, decision=decision)
        return result
