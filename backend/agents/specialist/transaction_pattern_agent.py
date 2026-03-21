"""Transaction Pattern Agent — velocity, structuring, layering, peer deviation."""

from __future__ import annotations

import json
from typing import Any, Dict

from backend.agents.specialist.base_agent import BaseSpecialistAgent
from backend.config import settings
from backend.models.agent_output import AgentName
from backend.models.alert import Alert


class TransactionPatternAgent(BaseSpecialistAgent):
    AGENT_NAME = "transaction-pattern-agent"
    AGENT_ENUM = AgentName.TRANSACTION_PATTERN
    INDEX_NAME = settings.azure_search_transactions_index

    def _get_instructions(self) -> str:
        return (
            "You are the Transaction Pattern Agent. Analyse transaction graphs for behavioural "
            "anomalies. Detect:\n"
            "  - Velocity spikes (>3x 30-day average in a single day)\n"
            "  - Structuring: multiple sub-$10,000 cash transactions to avoid CTR\n"
            "  - Layering: rapid movement of funds across multiple accounts\n"
            "  - Peer-group deviation: transaction behaviour unlike similar account cohort\n"
            "  - Round-number transactions and unusual timing patterns\n"
            "  - High-risk jurisdiction counterparties\n"
            "Provide feature attribution for explainability. "
            "Return JSON: {finding, risk_score (0-1), confidence (0-1), "
            "evidence_summary, flags[], anomaly_scores:{velocity, structuring, layering, peer_deviation}}"
        )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        txn_ids = alert.transaction_ids[:10] if alert.transaction_ids else []
        return (
            f"Analyse transaction patterns for account: {alert.account_id}\n"
            f"Customer: {alert.customer_name or 'Unknown'}\n"
            f"Alert typology: {alert.typology}\n"
            f"Total amount flagged: ${alert.amount:,.2f}\n"
            f"Transaction IDs (sample): {json.dumps(txn_ids)}\n"
            f"Is SWIFT: {alert.is_swift}\n"
            f"Account history: {context.get('account_history_summary', '')}\n\n"
            "Retrieve and analyse recent transactions for this account. "
            "Compute velocity, structuring, layering, and peer-group deviation scores. "
            "Return structured JSON with anomaly scores and risk assessment."
        )

    def _model(self) -> str:
        return settings.model_gpt4o
