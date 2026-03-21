"""Pydantic models for Suspicious Activity Reports (SAR)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SARStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    APPROVED = "APPROVED"
    FILED = "FILED"
    REJECTED = "REJECTED"


class SARFilingType(str, Enum):
    INITIAL = "INITIAL"
    CONTINUING = "CONTINUING"
    JOINT = "JOINT"


class SARNarrative(BaseModel):
    """FinCEN Form 111 (SAR) narrative — agent-drafted, analyst-approved."""

    # Part I — Reporting Financial Institution
    institution_name: str = ""
    institution_id: str = ""
    filing_date: Optional[datetime] = None
    prior_sar_filed: bool = False

    # Part II — Suspicious Activity
    subject_name: str = ""
    subject_dob: Optional[str] = None
    subject_address: str = ""
    subject_ssn_tin: str = ""  # masked
    subject_occupation: str = ""

    # Part III — Suspicious Activity Information
    activity_start_date: Optional[datetime] = None
    activity_end_date: Optional[datetime] = None
    total_amount: float = 0.0
    currency: str = "USD"
    suspicious_activity_types: List[str] = Field(default_factory=list)

    # Part IV — Narrative
    narrative_text: str = ""  # LLM-drafted, human-refined
    supporting_evidence: List[str] = Field(default_factory=list)
    transaction_ids: List[str] = Field(default_factory=list)

    # Agent drafting metadata
    drafted_by_agent: bool = False
    agent_confidence: float = 0.0
    groundedness_score: Optional[float] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class SAR(BaseModel):
    id: str
    case_id: str
    alert_ids: List[str] = Field(default_factory=list)
    status: SARStatus = SARStatus.DRAFT
    filing_type: SARFilingType = SARFilingType.INITIAL
    narrative: SARNarrative = Field(default_factory=SARNarrative)
    drafted_at: datetime = Field(default_factory=datetime.utcnow)
    analyst_reviewed_at: Optional[datetime] = None
    compliance_reviewed_at: Optional[datetime] = None
    filed_at: Optional[datetime] = None
    fincen_confirmation_number: Optional[str] = None
    reviewer_username: Optional[str] = None
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SARDraftRequest(BaseModel):
    """Request to auto-draft a SAR from a case."""

    case_id: str
    alert_ids: List[str]
    filing_type: SARFilingType = SARFilingType.INITIAL
    additional_context: Optional[str] = None


class SARApproval(BaseModel):
    reviewer_username: str
    approved: bool
    comments: Optional[str] = None
