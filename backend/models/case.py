"""Pydantic models for cases."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    PENDING_SAR = "PENDING_SAR"
    SAR_FILED = "SAR_FILED"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class CaseTier(str, Enum):
    TIER_1 = "TIER_1"  # Alert triage — high automation
    TIER_2 = "TIER_2"  # Case investigation — agent-assisted
    TIER_3 = "TIER_3"  # SAR filing — human sign-off required


class EvidenceItem(BaseModel):
    type: str  # "transaction_graph" | "media_hit" | "sanctions_match" | ...
    title: str
    content: str
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Case(BaseModel):
    id: str
    alert_ids: List[str] = Field(default_factory=list)
    account_id: str
    customer_name: Optional[str] = None
    status: CaseStatus = CaseStatus.OPEN
    tier: CaseTier = CaseTier.TIER_1
    assigned_analyst: Optional[str] = None
    risk_score: float = 0.0
    composite_flags: List[str] = Field(default_factory=list)
    evidence_package: List[EvidenceItem] = Field(default_factory=list)
    orchestrator_result_id: Optional[str] = None
    notes: List[Dict[str, Any]] = Field(default_factory=list)
    sar_draft_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseCreate(BaseModel):
    account_id: str
    alert_ids: List[str] = Field(default_factory=list)
    customer_name: Optional[str] = None
    tier: CaseTier = CaseTier.TIER_1


class CaseNote(BaseModel):
    author: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_system: bool = False
