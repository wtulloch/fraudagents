"""
Fraud Agent — multi-step chain-of-thought reasoning for novel fraud patterns.
Uses o3-mini (reasoning model) for complex fraud analysis.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class FraudAgent(BaseSpecialistAgent):
    AGENT_NAME = "fraud-agent"
    AGENT_ENUM = AgentName.FRAUD
    INDEX_NAME = settings.azure_search_transactions_index

    def _get_instructions(self) -> str:
        return (
            "You are the Fraud Detection Agent. Use multi-step chain-of-thought reasoning to "
            "identify fraud patterns. Analyse:\n"
            "  - Account Takeover: geo/device anomalies, credential-stuffing indicators\n"
            "  - Synthetic Identity: inconsistencies in KYC attributes, thin-file patterns\n"
            "  - First-Party Fraud: deliberate credit default patterns\n"
            "  - Card Fraud: high-frequency small transactions, card-not-present patterns\n"
            "  - Payment Fraud: mule account patterns, rapid fund egress\n"
            "  - Wire Fraud: social engineering patterns in transaction narratives\n"
            "Think step-by-step, consider multiple hypotheses, then converge on evidence-based risk score.\n"
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], fraud_indicators:{}, reasoning_steps[]}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        metadata = alert.metadata or {}
        return (
            f"Perform deep fraud analysis on alert:\n"
            f"Alert ID: {alert.id}\n"
            f"Account ID: {alert.account_id}\n"
            f"Customer: {alert.customer_name or 'Unknown'}\n"
            f"Typology: {alert.typology}\n"
            f"Amount: ${alert.amount:,.2f}\n"
            f"Transaction count: {len(alert.transaction_ids)}\n"
            f"Metadata: {json.dumps(metadata, default=str)[:500]}\n"
            f"Account history: {context.get('account_history_summary', '')}\n\n"
            "Reason step-by-step through possible fraud vectors. Consider device fingerprints, "
            "geo-location patterns, transaction velocity, and behavioural anomalies. "
            "Return structured JSON with reasoning steps."
        )

    def _model(self) -> str:
        return settings.model_o3_mini
