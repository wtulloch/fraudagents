"""
Base class for all specialist agents.

Each specialist agent:
  1. Builds a RAG-grounded system prompt using the appropriate AI Search index
  2. Invokes the Foundry agent via MAF (azure-ai-agents SDK)
  3. Parses and validates the structured JSON output
  4. Returns a typed AgentOutput

Subclasses only need to define: AGENT_NAME, INDEX_NAME, INSTRUCTIONS_ADDENDUM,
and optionally override `_build_user_message`.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional

import structlog

from backend.config import settings
from backend.models.agent_output import AgentName, AgentOutput, Citation, RiskLevel
from backend.models.alert import Alert
from backend.services.foundry_service import FoundryService
from backend.services.rag_service import RAGPipeline
from backend.services.search_service import SearchService

logger = structlog.get_logger(__name__)


def _score_to_level(score: float) -> RiskLevel:
    if score >= 0.80:
        return RiskLevel.CRITICAL
    if score >= 0.60:
        return RiskLevel.HIGH
    if score >= 0.35:
        return RiskLevel.MEDIUM
    if score >= 0.15:
        return RiskLevel.LOW
    return RiskLevel.NEGLIGIBLE


class BaseSpecialistAgent:
    AGENT_NAME: str = ""
    AGENT_ENUM: AgentName = AgentName.FRAUD
    INDEX_NAME: str = ""

    def __init__(self, foundry: FoundryService, search: SearchService) -> None:
        self.foundry = foundry
        self.search = search
        self.rag = RAGPipeline(search)

    async def analyze(self, alert: Alert, context: Dict[str, Any]) -> AgentOutput:
        t0 = time.monotonic()
        user_message = self._build_user_message(alert, context)

        try:
            # Layer 5: Prompt Shields (checked inside RAGPipeline.run)
            # Layer 1: RAG grounding
            grounded_system, hits = await self.rag.build_grounded_prompt(
                query=user_message,
                index_name=self.INDEX_NAME,
                base_instructions=self._get_instructions(),
                entity_id=alert.account_id,
            )
            source_texts = [h["content"] for h in hits]
            citations_raw = [
                {"source": h["source"], "document_id": h["id"], "relevance_score": h["score"]}
                for h in hits
            ]

            # Invoke Foundry agent via MAF
            run_result = await self.foundry.run_agent(
                agent_name=self.AGENT_NAME,
                user_message=f"[GROUNDED SYSTEM]\n{grounded_system}\n\n[USER]\n{user_message}",
            )

            raw_text = run_result.get("response_text", "")

            # Parse structured JSON output
            parsed = self.rag._parse_agent_json(raw_text)

            # Layer 2: Groundedness check
            ground_result = await self.rag.check_groundedness(raw_text, source_texts)
            groundedness_score = ground_result.get("score")
            is_grounded = ground_result.get("grounded", True)
            if ground_result.get("corrected_text") and not is_grounded:
                parsed["finding"] = ground_result["corrected_text"]

            risk_score = float(parsed.get("risk_score", 0.5))
            confidence = float(parsed.get("confidence", 0.5))
            latency_ms = int((time.monotonic() - t0) * 1000)

            return AgentOutput(
                agent_name=self.AGENT_ENUM,
                alert_id=alert.id,
                run_id=run_result.get("run_id", str(uuid.uuid4())),
                thread_id=run_result.get("thread_id"),
                model_used=self._model(),
                finding=parsed.get("finding", ""),
                risk_score=min(max(risk_score, 0.0), 1.0),
                risk_level=_score_to_level(risk_score),
                confidence=min(max(confidence, 0.0), 1.0),
                citations=[Citation(**c) for c in citations_raw],
                evidence_summary=parsed.get("evidence_summary", ""),
                flags=parsed.get("flags", []),
                groundedness_score=groundedness_score,
                is_grounded=is_grounded,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error("agent_error", agent=self.AGENT_NAME, alert_id=alert.id, error=str(e))
            latency_ms = int((time.monotonic() - t0) * 1000)
            return AgentOutput(
                agent_name=self.AGENT_ENUM,
                alert_id=alert.id,
                run_id=str(uuid.uuid4()),
                model_used=self._model(),
                finding=f"Agent failed: {str(e)[:300]}",
                risk_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                confidence=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )

    def _build_user_message(self, alert: Alert, context: Dict[str, Any]) -> str:
        """Build the user-facing message for this agent. Override to customise."""
        return (
            f"Analyse the following alert for {self.__class__.__name__} risk indicators.\n\n"
            f"Alert ID: {alert.id}\n"
            f"Account ID: {alert.account_id}\n"
            f"Customer: {alert.customer_name or 'Unknown'}\n"
            f"Typology: {alert.typology}\n"
            f"Amount: ${alert.amount:,.2f} {alert.currency if alert.amount else ''}\n"
            f"Description: {alert.description or 'N/A'}\n"
            f"Is PEP: {alert.is_pep}\n"
            f"Is SWIFT: {alert.is_swift}\n"
            f"Account History: {context.get('account_history_summary', 'N/A')}\n\n"
            "Return a JSON object with keys: "
            "finding, risk_score (0-1), confidence (0-1), citation[], evidence_summary, flags[]."
        )

    def _get_instructions(self) -> str:
        """Return agent system instructions. Override to provide specific instructions."""
        return f"You are the {self.__class__.__name__}."

    def _model(self) -> str:
        return settings.model_gpt4o
