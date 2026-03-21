"""KYC/KYB Lookup Agent — entity resolution, UBO chains, jurisdiction risk."""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class KYCKYBAgent(BaseSpecialistAgent):
    AGENT_NAME = "kyc-kyb-agent"
    AGENT_ENUM = AgentName.KYC_KYB
    INDEX_NAME = settings.azure_search_kyc_index

    def _get_instructions(self) -> str:
        return (
            "You are the KYC/KYB Lookup Agent. Perform entity resolution against internal "
            "CIF data and external registries. Identify:\n"
            "  - Identity discrepancies or mismatches\n"
            "  - Beneficial ownership (UBO) gaps or missing disclosure\n"
            "  - Dormant-entity reactivation patterns\n"
            "  - Jurisdiction risk (FATF grey/black list countries)\n"
            "  - Counterparty network complexity (shell company indicators)\n"
            "  - PEP connections in the ownership chain\n"
            "  - Verification status and last review date staleness\n"
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], ubo_flags[], jurisdiction_risk_score}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        return (
            f"Perform KYC/KYB lookup for entity:\n"
            f"Account ID: {alert.account_id}\n"
            f"Customer Name: {alert.customer_name or 'Unknown'}\n"
            f"Is PEP: {alert.is_pep}\n"
            f"Alert typology: {alert.typology}\n"
            f"Account history: {context.get('account_history_summary', '')}\n\n"
            "Retrieve the KYC record and assess: identity verification status, "
            "beneficial ownership completeness, jurisdiction risk, dormancy indicators, "
            "and PEP/sanctions status. Return structured JSON."
        )

    def _model(self) -> str:
        return settings.model_gpt4o
