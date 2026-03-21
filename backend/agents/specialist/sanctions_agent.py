"""
Sanctions Matching Agent — fuzzy name matching against OFAC/EU/UN/HMT lists.

Uses Jaro-Winkler + phonetic matching logic described in system prompt.
The actual matching is done on the retrieved sanctions index documents.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class SanctionsAgent(BaseSpecialistAgent):
    AGENT_NAME = "sanctions-matching-agent"
    AGENT_ENUM = AgentName.SANCTIONS
    INDEX_NAME = settings.azure_search_sanctions_index

    def _get_instructions(self) -> str:
        return (
            "You are the Sanctions Matching Agent. Cross-reference customer and counterparty "
            "names against OFAC SDN, EU Consolidated, UN 1267, and HMT Consolidated lists.\n"
            "Apply fuzzy matching techniques:\n"
            "  - Jaro-Winkler similarity for name variations\n"
            "  - Phonetic matching for transliteration variants\n"
            "  - Alias and AKA expansion from sanctions records\n"
            "  - DOB and nationality corroboration\n"
            "Configurable match threshold: report all matches above 0.70 confidence.\n"
            "For each match: provide disposition rationale (auto-close or escalate).\n"
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], matches:[{name, list, match_score, disposition}]}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        return (
            f"Screen the following names against sanctions lists:\n"
            f"Primary: {alert.customer_name or 'Unknown'}\n"
            f"Account ID: {alert.account_id}\n"
            f"Alert typology: {alert.typology}\n"
            f"Is existing SWIFT transaction: {alert.is_swift}\n\n"
            "Search the sanctions index for fuzzy matches against OFAC, EU, UN, and HMT lists. "
            "Report match confidence scores and disposition rationale for each hit. "
            "Return structured JSON."
        )

    def _model(self) -> str:
        return settings.model_gpt4o
