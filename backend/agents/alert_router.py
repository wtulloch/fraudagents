"""
Alert Router — ingests raw alert events and builds enriched context
objects for consumption by the specialist agents.

Determines:
  • Which specialist agents should be invoked (based on typology)
  • HITL flags (PEP, high-value, SWIFT)
  • Initial context enrichment from Cosmos DB
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

import structlog

from backend.models.alert import Alert, AlertTypology

logger = structlog.get_logger(__name__)

# Typology → required agents mapping
TYPOLOGY_AGENT_MAP: Dict[str, Set[str]] = {
    # AML typologies
    AlertTypology.STRUCTURING: {"transaction-pattern-agent", "kyc-kyb-agent", "aml-agent"},
    AlertTypology.LAYERING: {"transaction-pattern-agent", "kyc-kyb-agent", "aml-agent", "adverse-media-agent"},
    AlertTypology.PLACEMENT: {"transaction-pattern-agent", "kyc-kyb-agent", "aml-agent"},
    AlertTypology.INTEGRATION: {"transaction-pattern-agent", "kyc-kyb-agent", "aml-agent"},
    AlertTypology.WIRE_FRAUD: {"transaction-pattern-agent", "kyc-kyb-agent", "sanctions-matching-agent", "fraud-agent"},
    AlertTypology.SANCTIONS_EVASION: {"sanctions-matching-agent", "transaction-pattern-agent", "kyc-kyb-agent", "aml-agent"},
    AlertTypology.PEP_ACTIVITY: {"adverse-media-agent", "kyc-kyb-agent", "sanctions-matching-agent", "aml-agent"},
    AlertTypology.HIGH_RISK_JURISDICTION: {"transaction-pattern-agent", "kyc-kyb-agent", "sanctions-matching-agent"},
    AlertTypology.ADVERSE_MEDIA: {"adverse-media-agent", "kyc-kyb-agent"},
    AlertTypology.TRADE_BASED_ML: {"transaction-pattern-agent", "kyc-kyb-agent", "aml-agent"},
    # Fraud typologies
    AlertTypology.ACCOUNT_TAKEOVER: {"fraud-agent", "transaction-pattern-agent", "kyc-kyb-agent"},
    AlertTypology.IDENTITY_THEFT: {"fraud-agent", "kyc-kyb-agent", "adverse-media-agent"},
    AlertTypology.CARD_FRAUD: {"fraud-agent", "transaction-pattern-agent"},
    AlertTypology.SYNTHETIC_IDENTITY: {"fraud-agent", "kyc-kyb-agent", "adverse-media-agent"},
    AlertTypology.FIRST_PARTY_FRAUD: {"fraud-agent", "transaction-pattern-agent", "kyc-kyb-agent"},
    AlertTypology.PAYMENT_FRAUD: {"fraud-agent", "transaction-pattern-agent"},
    # Unknown — run all agents
    AlertTypology.UNKNOWN: {
        "adverse-media-agent", "transaction-pattern-agent", "kyc-kyb-agent",
        "sanctions-matching-agent", "fraud-agent", "aml-agent",
    },
}

# Always include these agents for all alerts
ALWAYS_RUN = {"transaction-pattern-agent", "kyc-kyb-agent"}


class AlertRouter:
    def __init__(self, cosmos_service) -> None:
        self.cosmos = cosmos_service

    async def route(self, alert: Alert) -> Dict[str, Any]:
        """
        Build an enriched alert context dict for the orchestrator.
        Returns which agents to invoke and the enriched alert payload.
        """
        # Determine agent set from typology
        typology_agents = TYPOLOGY_AGENT_MAP.get(alert.typology, TYPOLOGY_AGENT_MAP[AlertTypology.UNKNOWN])
        agents_to_invoke = list(typology_agents | ALWAYS_RUN)

        # HITL pre-flags
        hitl_flags: List[str] = []
        if alert.is_pep:
            hitl_flags.append("PEP_ACCOUNT")
            if "adverse-media-agent" not in agents_to_invoke:
                agents_to_invoke.append("adverse-media-agent")
        if alert.is_swift:
            hitl_flags.append("SWIFT_TRANSACTION")
        if alert.is_high_value:
            hitl_flags.append("HIGH_VALUE")

        # Pull any existing case for this account
        existing_cases = await self.cosmos.query(
            "cases",
            "SELECT c.id, c.status FROM c WHERE c.account_id = @account_id",
            [{"name": "@account_id", "value": alert.account_id}],
        )

        context = {
            "alert": alert.model_dump(mode="json"),
            "agents_to_invoke": agents_to_invoke,
            "hitl_pre_flags": hitl_flags,
            "existing_cases": existing_cases,
            "account_history_summary": await self._get_account_summary(alert.account_id),
        }

        logger.info(
            "alert_routed",
            alert_id=alert.id,
            typology=alert.typology,
            agents=agents_to_invoke,
            hitl_flags=hitl_flags,
        )
        return context

    async def _get_account_summary(self, account_id: str) -> str:
        """Quick account risk summary from prior alerts."""
        prior_alerts = await self.cosmos.query(
            "alerts",
            "SELECT c.typology, c.status, c.created_at FROM c WHERE c.account_id = @id ORDER BY c.created_at DESC OFFSET 0 LIMIT 10",
            [{"name": "@id", "value": account_id}],
        )
        if not prior_alerts:
            return "No prior alerts on this account."
        return (
            f"{len(prior_alerts)} prior alert(s) found. "
            + ", ".join(f"{a['typology']}:{a['status']}" for a in prior_alerts[:3])
        )
