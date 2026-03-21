"""
Central configuration — all values read from .env via pydantic-settings.
Never hard-code secrets; reference os.environ or this Settings object everywhere.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Azure AI Foundry / MAF ────────────────────────────────────────────────
    azure_ai_foundry_project_endpoint: str = Field(alias="AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    azure_ai_foundry_project_connection_string: Optional[str] = Field(
        default=None, alias="AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING"
    )

    # ── Model Deployments (Model Router) ─────────────────────────────────────
    model_gpt4o_mini: str = Field(default="gpt-4o-mini", alias="MODEL_GPT4O_MINI")
    model_gpt4o: str = Field(default="gpt-4o", alias="MODEL_GPT4O")
    model_o3_mini: str = Field(default="o3-mini", alias="MODEL_O3_MINI")
    model_embedding: str = Field(default="text-embedding-3-large", alias="MODEL_EMBEDDING")

    # ── Azure OpenAI (Responses API v2) ──────────────────────────────────────
    azure_openai_endpoint: str = Field(alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        default="2025-01-01-preview", alias="AZURE_OPENAI_API_VERSION"
    )

    # ── Azure AI Search ───────────────────────────────────────────────────────
    azure_search_endpoint: str = Field(alias="AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str = Field(alias="AZURE_SEARCH_API_KEY")
    azure_search_transactions_index: str = Field(
        default="transactions-index", alias="AZURE_SEARCH_TRANSACTIONS_INDEX"
    )
    azure_search_kyc_index: str = Field(default="kyc-index", alias="AZURE_SEARCH_KYC_INDEX")
    azure_search_media_index: str = Field(
        default="media-index", alias="AZURE_SEARCH_MEDIA_INDEX"
    )
    azure_search_sanctions_index: str = Field(
        default="sanctions-index", alias="AZURE_SEARCH_SANCTIONS_INDEX"
    )

    # ── Azure AD Service Principal ───────────────────────────────────────────────
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = Field(default=None, alias="AZURE_CLIENT_SECRET")

    # ── Azure Cosmos DB ───────────────────────────────────────────────────────
    azure_cosmos_endpoint: str = Field(alias="AZURE_COSMOS_ENDPOINT")
    # If empty, CosmosService will use ClientSecretCredential (or DefaultAzureCredential fallback)
    azure_cosmos_key: Optional[str] = Field(default=None, alias="AZURE_COSMOS_KEY")
    azure_cosmos_database: str = Field(
        default="fraud-detection-db", alias="AZURE_COSMOS_DATABASE"
    )

    # ── Azure Content Safety (optional — hallucination prevention degrades gracefully if absent) ──
    azure_content_safety_endpoint: Optional[str] = Field(default=None, alias="AZURE_CONTENT_SAFETY_ENDPOINT")
    azure_content_safety_key: Optional[str] = Field(default=None, alias="AZURE_CONTENT_SAFETY_KEY")

    # ── Application ───────────────────────────────────────────────────────────
    app_secret_key: str = Field(default="change-me-in-production", alias="APP_SECRET_KEY")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    # ── Risk Thresholds ───────────────────────────────────────────────────────
    risk_sar_threshold: float = Field(default=0.75, alias="RISK_SAR_THRESHOLD")
    risk_escalate_threshold: float = Field(default=0.50, alias="RISK_ESCALATE_THRESHOLD")
    risk_auto_close_threshold: float = Field(default=0.25, alias="RISK_AUTO_CLOSE_THRESHOLD")

    # ── HITL Thresholds ───────────────────────────────────────────────────────
    hitl_pep_threshold: float = Field(default=0.70, alias="HITL_PEP_THRESHOLD")
    hitl_high_value_amount: float = Field(default=100_000.0, alias="HITL_HIGH_VALUE_AMOUNT")
    hitl_swift_require_review: bool = Field(default=True, alias="HITL_SWIFT_REQUIRE_REVIEW")

    # ── Groundedness ──────────────────────────────────────────────────────────
    groundedness_score_threshold: float = Field(
        default=3.5, alias="GROUNDEDNESS_SCORE_THRESHOLD"
    )
    groundedness_correction_enabled: bool = Field(
        default=True, alias="GROUNDEDNESS_CORRECTION_ENABLED"
    )

    # ── Synthetic Data ────────────────────────────────────────────────────────
    synthetic_seed: int = Field(default=42, alias="SYNTHETIC_SEED")
    synthetic_default_records: int = Field(default=500, alias="SYNTHETIC_DEFAULT_RECORDS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
