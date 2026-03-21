"""AML Agent — placement, layering, integration, structuring, and TBML patterns."""

from __future__ import annotations

from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class AMLAgent(BaseSpecialistAgent):
    AGENT_NAME = "aml-agent"
    AGENT_ENUM = AgentName.AML
    INDEX_NAME = settings.azure_search_transactions_index

    def _get_instructions(self) -> str:
        return (
            "You are the Anti-Money Laundering (AML) Agent. Detect money laundering patterns:\n"
            "  - Placement: introducing illicit cash into the financial system\n"
            "  - Layering: concealing the trail through complex transaction chains\n"
            "  - Integration: re-entering laundered funds into the legitimate economy\n"
            "  - Structuring (smurfing): breaking large amounts into sub-CTR transactions\n"
            "  - Trade-Based Money Laundering (TBML): over/under-invoicing patterns\n"
            "  - Real Estate and high-value asset purchases\n"
            "  - Misuse of shell companies and nominee accounts\n"
            "Assess the full transaction flow, not just individual transactions.\n"
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], aml_stage, ml_indicators[]}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        return (
            f"Perform AML analysis on alert:\n"
            f"Alert ID: {alert.id}\n"
            f"Account ID: {alert.account_id}\n"
            f"Customer: {alert.customer_name or 'Unknown'}\n"
            f"Typology: {alert.typology}\n"
            f"Total amount: ${alert.amount:,.2f}\n"
            f"Is SWIFT: {alert.is_swift}\n"
            f"Account history: {context.get('account_history_summary', '')}\n\n"
            "Analyse the transaction flow for money laundering indicators. "
            "Identify the AML stage (placement/layering/integration), "
            "assess counterparty risk, and evaluate structuring patterns. "
            "Return structured JSON."
        )

    def _model(self) -> str:
        return settings.model_gpt4o
