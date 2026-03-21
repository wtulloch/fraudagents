"""Adverse Media Agent — queries media corpus and PEP/watchlists via RAG."""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class AdverseMediaAgent(BaseSpecialistAgent):
    AGENT_NAME = "adverse-media-agent"
    AGENT_ENUM = AgentName.ADVERSE_MEDIA
    INDEX_NAME = settings.azure_search_media_index

    def _get_instructions(self) -> str:
        return (
            "You are the Adverse Media Agent in a financial crime detection system. "
            "Assess reputational risk for the subject by analysing retrieved news, "
            "PEP lists, and sanctions feeds. "
            "Identify: negative press about financial crimes, fraud, corruption; "
            "PEP connections; adverse regulatory actions; criminal proceedings. "
            "Always ground findings in retrieved documents. "
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], citations[{source, document_id, relevance_score}]}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        return (
            f"Search for adverse media on customer: {alert.customer_name or alert.account_id}\n"
            f"Account ID: {alert.account_id}\n"
            f"Is PEP: {alert.is_pep}\n"
            f"Alert typology: {alert.typology}\n"
            f"Context: {context.get('account_history_summary', '')}\n\n"
            "Search the media index for any negative news, PEP references, sanctions hits, "
            "or regulatory actions related to this customer. "
            "Return a structured JSON response with risk assessment."
        )

    def _model(self) -> str:
        return settings.model_gpt4o
