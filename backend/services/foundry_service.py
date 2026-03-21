"""
Azure AI Foundry service  Foundry Projects v2 API.

Responsibilities:
   Create / retrieve specialist agents in Foundry via create_version() (idempotent)
   Run agents via the Responses API v2 with agent_reference (no thread polling)
   Expose direct one-shot completions via the Responses API

Uses azure-ai-projects 2.x (AIProjectClient) with PromptAgentDefinition.
"""

from __future__ import annotations

import uuid
import time
from typing import Any, Callable, Dict, Optional

import structlog
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.core.pipeline.policies import HeadersPolicy
from azure.identity.aio import ClientSecretCredential, DefaultAzureCredential

from backend.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Agent registry  name  {model, instructions}
# ---------------------------------------------------------------------------
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "adverse-media-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Adverse Media Agent in a financial crime detection system. "
            "Your role is to assess reputational risk for a given subject by analysing "
            "retrieved news articles, PEP (Politically Exposed Person) lists, and sanctions feeds. "
            "Always ground your findings in retrieved evidence. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[]."
        ),
    },
    "transaction-pattern-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Transaction Pattern Agent. Analyse transaction graphs for behavioural "
            "anomalies including velocity spikes, structuring (sub-CTR transactions), "
            "layering, and peer-group deviation. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[]."
        ),
    },
    "kyc-kyb-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the KYC/KYB Lookup Agent. Perform real-time entity resolution against "
            "internal CIF data and external registries. Build beneficial ownership chains, "
            "identify UBO gaps, dormant-entity reactivation, and jurisdiction risk. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[]."
        ),
    },
    "sanctions-matching-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Sanctions Matching Agent. Perform fuzzy name matching (Jaro-Winkler, "
            "phonetic, transliteration-aware) against OFAC, EU, UN, and HMT watchlists. "
            "Cross-reference with configurable match thresholds. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[], match_confidence."
        ),
    },
    "fraud-agent": {
        "model": settings.model_o3_mini,
        "instructions": (
            "You are the Fraud Detection Agent. Use multi-step chain-of-thought reasoning to "
            "identify novel fraud patterns including account takeover, synthetic identity, "
            "first-party fraud, payment fraud, and card fraud. "
            "Consider device fingerprints, geo-location anomalies, and behavioural biometrics. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[]."
        ),
    },
    "aml-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Anti-Money Laundering (AML) Agent. Detect placement, layering, and "
            "integration patterns in transaction flows. Identify structuring, trade-based money "
            "laundering, and sanctions evasion. "
            "Return a structured JSON with: finding, risk_score (0-1), confidence (0-1), "
            "citations[], evidence_summary, flags[]."
        ),
    },
    "sar-drafting-agent": {
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the SAR Drafting Agent. Draft FinCEN Form 111 SAR narratives from "
            "structured evidence packages assembled by the specialist agents. "
            "Narratives must be factual, cite sources, and follow FinCEN guidance. "
            "Do not include ungrounded information. "
            "Return the narrative as structured JSON matching the SARNarrative schema."
        ),
    },
}


class FoundryService:
    def __init__(self) -> None:
        if (
            settings.azure_tenant_id
            and settings.azure_client_id
            and settings.azure_client_secret
        ):
            self._credential = ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
        else:
            self._credential = DefaultAzureCredential()
        self._project_client: Optional[AIProjectClient] = None
        self._openai_client = None  # AsyncOpenAI  obtained from project client
        self._agent_id_cache: Dict[str, str] = {}  # agent_name  agent id

    # ------------------------------------------------------------------
    # Lazy client properties
    # ------------------------------------------------------------------

    @property
    def project_client(self) -> AIProjectClient:
        if self._project_client is None:
            # azure-core's aiohttp transport sets auto_decompress=False, so the
            # Foundry API's gzip-compressed responses are never decompressed before
            # the UTF-8 decoder runs.  Sending Accept-Encoding: identity tells the
            # server to return plain (uncompressed) JSON instead.
            _no_gzip = HeadersPolicy(base_headers={"Accept-Encoding": "identity"})
            self._project_client = AIProjectClient(
                endpoint=settings.azure_ai_foundry_project_endpoint,
                credential=self._credential,
                headers_policy=_no_gzip,
            )
        return self._project_client

    @property
    def openai_client(self):
        """Lazy-initialise the AsyncOpenAI client from the project client."""
        if self._openai_client is None:
            self._openai_client = self.project_client.get_openai_client()
        return self._openai_client

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    async def ensure_agents(self) -> None:
        """Create or retrieve all specialist agents in Foundry (idempotent)."""
        failed: list[str] = []
        for agent_name, spec in AGENT_REGISTRY.items():
            try:
                agent_id = await self._get_or_create_agent(agent_name, spec)
                self._agent_id_cache[agent_name] = agent_id
                logger.info("agent_ready", name=agent_name, agent_id=agent_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("agent_init_failed", name=agent_name, error=str(exc))
                failed.append(agent_name)
        if failed:
            logger.warning("some_agents_unavailable", agents=failed)

    async def _get_or_create_agent(self, name: str, spec: Dict[str, Any]) -> str:
        """
        Return the id of an existing agent version by name, or create a new
        prompt agent using the Foundry Projects v2 create_version() API.

        If agents.list() fails (e.g. SDK decode error), falls through to
        create_version() which is idempotent on the Foundry side.
        """
        # Try listing existing agents first to avoid duplicate creation
        try:
            async for agent in self.project_client.agents.list():
                if agent.name == name:
                    logger.info("agent_found", name=name, agent_id=agent.id)
                    return agent.id
        except Exception as list_exc:  # noqa: BLE001
            logger.warning(
                "agent_list_failed_falling_through_to_create",
                name=name,
                error=str(list_exc),
            )

        # Not found (or list failed) — create a new prompt agent version
        version = await self.project_client.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(
                model=spec["model"],
                instructions=spec["instructions"],
            ),
        )
        logger.info("agent_created", name=name, agent_id=version.id, version=version.version)
        return version.id

    def get_agent_id(self, name: str) -> Optional[str]:
        return self._agent_id_cache.get(name)

    # ------------------------------------------------------------------
    # Run agent  Responses API v2 with agent_reference
    # ------------------------------------------------------------------

    async def run_agent(
        self,
        agent_name: str,
        user_message: str,
        tool_handlers: Optional[Dict[str, Callable[..., Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a named Foundry agent via the Responses API v2.

        Uses openai.responses.create() with agent_reference so the agent's
        system prompt, tools, and model config are applied server-side.

        Returns:
            {run_id, thread_id, agent_name, status, response_text, latency_ms}
        """
        t0 = time.monotonic()

        # Lazy init: if the agent wasn't registered at startup, try now
        if agent_name not in self._agent_id_cache:
            spec = AGENT_REGISTRY.get(agent_name)
            if spec:
                try:
                    agent_id = await self._get_or_create_agent(agent_name, spec)
                    self._agent_id_cache[agent_name] = agent_id
                except Exception as exc:  # noqa: BLE001
                    logger.warning("agent_lazy_init_failed", name=agent_name, error=str(exc))

        # Create a new conversation (maintains history for multi-turn if needed)
        conversation = await self.openai_client.conversations.create()

        response = await self.openai_client.responses.create(
            conversation=conversation.id,
            extra_body={
                "agent_reference": {"name": agent_name, "type": "agent_reference"}
            },
            input=user_message,
        )

        latency_ms = int((time.monotonic() - t0) * 1000)
        response_text = response.output_text if hasattr(response, "output_text") else ""
        run_id = response.id if hasattr(response, "id") else str(uuid.uuid4())

        logger.info(
            "agent_run_complete",
            agent=agent_name,
            run_id=run_id,
            latency_ms=latency_ms,
        )

        return {
            "run_id": run_id,
            "thread_id": conversation.id,  # kept for backward compat
            "agent_name": agent_name,
            "status": "completed",
            "response_text": response_text,
            "latency_ms": latency_ms,
        }

    # ------------------------------------------------------------------
    # Direct Responses API v2 (one-shot completions, no agent_reference)
    # ------------------------------------------------------------------

    async def responses_create(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        One-shot completion via the Responses API v2 without agent_reference.
        """
        t0 = time.monotonic()

        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        kwargs: Dict[str, Any] = {
            "model": model,
            "input": input_messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["text"] = {"format": response_format}

        response = await self.openai_client.responses.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)
        content = response.output_text if hasattr(response, "output_text") else str(response)

        return {
            "response_id": response.id if hasattr(response, "id") else str(uuid.uuid4()),
            "model": model,
            "content": content,
            "latency_ms": latency_ms,
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        if self._openai_client:
            await self._openai_client.close()
        if self._project_client:
            await self._project_client.close()
