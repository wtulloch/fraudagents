"""
Model Router — selects the optimal Azure AI Foundry model for each task type.

Design spec:
  • Alert triage (L1)         → GPT-4o-mini   (~0.3s, high throughput)
  • Investigation analysis    → GPT-4o         (complex multi-source reasoning)
  • SAR narrative drafting    → GPT-4o         (LoRA-ready for institution templates)
  • Complex fraud reasoning   → o3-mini        (chain-of-thought, novel patterns)
  • Embedding generation      → text-embedding-3-large (3072d, Matryoshka)
"""

from __future__ import annotations

from enum import Enum

from backend.config import settings


class TaskType(str, Enum):
    ALERT_TRIAGE = "ALERT_TRIAGE"
    INVESTIGATION = "INVESTIGATION"
    SAR_DRAFTING = "SAR_DRAFTING"
    COMPLEX_FRAUD = "COMPLEX_FRAUD"
    EMBEDDING = "EMBEDDING"
    SANCTIONS_MATCHING = "SANCTIONS_MATCHING"
    KYC_LOOKUP = "KYC_LOOKUP"
    AML_ANALYSIS = "AML_ANALYSIS"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"


# Agent name → task type mapping
AGENT_TASK_MAP = {
    "adverse-media-agent": TaskType.ADVERSE_MEDIA,
    "transaction-pattern-agent": TaskType.INVESTIGATION,
    "kyc-kyb-agent": TaskType.KYC_LOOKUP,
    "sanctions-matching-agent": TaskType.SANCTIONS_MATCHING,
    "fraud-agent": TaskType.COMPLEX_FRAUD,
    "aml-agent": TaskType.AML_ANALYSIS,
    "sar-drafting-agent": TaskType.SAR_DRAFTING,
}


class ModelRouter:
    """Deterministic model selection — no LLM inference involved."""

    ROUTING_TABLE = {
        TaskType.ALERT_TRIAGE: settings.model_gpt4o_mini,
        TaskType.INVESTIGATION: settings.model_gpt4o,
        TaskType.SAR_DRAFTING: settings.model_gpt4o,
        TaskType.COMPLEX_FRAUD: settings.model_o3_mini,
        TaskType.EMBEDDING: settings.model_embedding,
        TaskType.SANCTIONS_MATCHING: settings.model_gpt4o,
        TaskType.KYC_LOOKUP: settings.model_gpt4o,
        TaskType.AML_ANALYSIS: settings.model_gpt4o,
        TaskType.ADVERSE_MEDIA: settings.model_gpt4o,
    }

    def route(self, task_type: TaskType) -> str:
        """Return the deployment name for the given task."""
        return self.ROUTING_TABLE.get(task_type, settings.model_gpt4o)

    def route_for_agent(self, agent_name: str) -> str:
        task = AGENT_TASK_MAP.get(agent_name, TaskType.INVESTIGATION)
        return self.route(task)

    def all_routes(self) -> dict:
        return {k.value: v for k, v in self.ROUTING_TABLE.items()}


# Singleton
model_router = ModelRouter()
