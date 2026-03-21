"""Pydantic models for fraud/AML alerts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertTypology(str, Enum):
    # Fraud typologies
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    IDENTITY_THEFT = "IDENTITY_THEFT"
    CARD_FRAUD = "CARD_FRAUD"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    FIRST_PARTY_FRAUD = "FIRST_PARTY_FRAUD"
    PAYMENT_FRAUD = "PAYMENT_FRAUD"
    # AML typologies
    STRUCTURING = "STRUCTURING"
    LAYERING = "LAYERING"
    PLACEMENT = "PLACEMENT"
    INTEGRATION = "INTEGRATION"
    WIRE_FRAUD = "WIRE_FRAUD"
    SANCTIONS_EVASION = "SANCTIONS_EVASION"
    PEP_ACTIVITY = "PEP_ACTIVITY"
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"
    TRADE_BASED_ML = "TRADE_BASED_ML"
    UNKNOWN = "UNKNOWN"


class AlertStatus(str, Enum):
    NEW = "NEW"
    ROUTING = "ROUTING"
    IN_INVESTIGATION = "IN_INVESTIGATION"
    PENDING_HITL = "PENDING_HITL"
    SAR_DRAFT = "SAR_DRAFT"
    SAR_FILED = "SAR_FILED"
    ESCALATED = "ESCALATED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
    CLOSED_SUSPICIOUS = "CLOSED_SUSPICIOUS"


class AlertPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertSource(str, Enum):
    TMS = "TMS"          # Transaction Monitoring System
    RULE_ENGINE = "RULE_ENGINE"
    ML_MODEL = "ML_MODEL"
    MANUAL = "MANUAL"
    THIRD_PARTY = "THIRD_PARTY"
    FEDNOW = "FEDNOW"
    SWIFT = "SWIFT"


class Alert(BaseModel):
    id: str
    case_id: Optional[str] = None
    account_id: str
    customer_name: Optional[str] = None
    typology: AlertTypology = AlertTypology.UNKNOWN
    status: AlertStatus = AlertStatus.NEW
    priority: AlertPriority = AlertPriority.MEDIUM
    source: AlertSource = AlertSource.TMS
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None  # analyst username
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_pep: bool = False
    is_high_value: bool = False
    is_swift: bool = False
    transaction_ids: List[str] = Field(default_factory=list)


class AlertCreate(BaseModel):
    account_id: str
    typology: AlertTypology = AlertTypology.UNKNOWN
    priority: AlertPriority = AlertPriority.MEDIUM
    source: AlertSource = AlertSource.TMS
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None
    transaction_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    priority: Optional[AlertPriority] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
