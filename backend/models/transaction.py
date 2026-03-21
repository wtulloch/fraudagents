"""Pydantic models for transactions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionChannel(str, Enum):
    ACH = "ACH"
    WIRE = "WIRE"
    SWIFT = "SWIFT"
    CARD = "CARD"
    FEDNOW = "FEDNOW"
    RTP = "RTP"
    ZELLE = "ZELLE"
    CHECK = "CHECK"
    CASH = "CASH"


class TransactionDirection(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class Transaction(BaseModel):
    id: str
    account_id: str
    counterparty_account_id: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_country: Optional[str] = None
    amount: float
    currency: str = "USD"
    channel: TransactionChannel
    direction: TransactionDirection
    timestamp: datetime
    description: Optional[str] = None
    reference_number: Optional[str] = None
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    geo_location: Optional[str] = None
    is_international: bool = False
    is_structured: bool = False  # below CTR threshold ($10k)
    swift_message_type: Optional[str] = None  # e.g. MT103


class TransactionGraph(BaseModel):
    """Transaction graph used by Transaction Pattern Agent."""

    account_id: str
    transactions: list[Transaction]
    total_volume_30d: float = 0.0
    total_count_30d: int = 0
    avg_transaction_30d: float = 0.0
    velocity_score: float = 0.0  # 0-1
    structuring_score: float = 0.0  # 0-1
    peer_group_deviation_score: float = 0.0  # 0-1
    layering_score: float = 0.0  # 0-1
    unique_counterparties_30d: int = 0
    high_risk_jurisdictions: list[str] = Field(default_factory=list)
