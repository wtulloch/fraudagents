"""Pydantic models for structured agent outputs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentName(str, Enum):
    ADVERSE_MEDIA = "adverse_media"
    TRANSACTION_PATTERN = "transaction_pattern"
    KYC_KYB = "kyc_kyb"
    SANCTIONS = "sanctions"
    FRAUD = "fraud"
    AML = "aml"
    RISK_AGGREGATOR = "risk_aggregator"
    DECISION_GATE = "decision_gate"


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEGLIGIBLE = "NEGLIGIBLE"


class Citation(BaseModel):
    source: str
    document_id: str
    relevance_score: float
    excerpt: Optional[str] = None


class AgentOutput(BaseModel):
    """Structured output contract for ALL specialist agents (RAG-grounded)."""

    agent_name: AgentName
    alert_id: str
    run_id: str  # Foundry agent run / response ID
    thread_id: Optional[str] = None  # Foundry thread ID
    model_used: str
    finding: str  # Human-readable summary
    risk_score: float = Field(ge=0.0, le=1.0)  # 0-1
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1
    citations: List[Citation] = Field(default_factory=list)
    evidence_summary: str = ""
    flags: List[str] = Field(default_factory=list)  # e.g. ["PEP_MATCH", "STRUCTURING"]
    groundedness_score: Optional[float] = None  # 1-5 from Content Safety
    is_grounded: bool = True
    raw_response: Optional[Dict[str, Any]] = None
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None  # populated if agent run failed


class RiskSignal(BaseModel):
    """Aggregated risk signal produced by RiskAggregator."""

    alert_id: str
    composite_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    agent_scores: Dict[str, float] = Field(default_factory=dict)
    dominant_typologies: List[str] = Field(default_factory=list)
    all_flags: List[str] = Field(default_factory=list)
    requires_hitl: bool = False
    hitl_reason: Optional[str] = None
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DecisionOutcome(str, Enum):
    SAR_FILE = "SAR_FILE"
    ESCALATE = "ESCALATE"
    CLOSE_NO_ACTION = "CLOSE_NO_ACTION"
    PENDING_HITL = "PENDING_HITL"


class DecisionResult(BaseModel):
    """Deterministic decision from Decision Gate (not LLM inference)."""

    alert_id: str
    outcome: DecisionOutcome
    rationale: str
    rule_triggered: str  # which deterministic rule fired
    risk_score: float
    risk_level: RiskLevel
    requires_sar: bool = False
    escalation_reason: Optional[str] = None
    auto_sar_eligible: bool = False  # can SAR be auto-drafted?
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrchestratorResult(BaseModel):
    """Full pipeline result returned to the API layer."""

    alert_id: str
    agent_outputs: List[AgentOutput]
    risk_signal: RiskSignal
    decision: DecisionResult
    total_latency_ms: int = 0
    pipeline_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
