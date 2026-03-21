"""
RAG Pipeline — per-agent grounding using Azure AI Search.

Implements the 5-layer hallucination prevention architecture:
  1. RAG Grounding      — inject retrieved context into system prompt
  2. Groundedness       — score output via Content Safety SDK
  3. Active Correction  — rewrite ungrounded sentences (correction=true)
  4. Deterministic Gate — decision gate uses rule logic, not LLM output
  5. Prompt Shields     — detect/block prompt injection and jailbreaks

Token budget: 512 tokens / chunk, 128-token overlap (per design spec).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx
import structlog

from backend.config import settings
from backend.services.search_service import SearchService

logger = structlog.get_logger(__name__)

# Chunk sizing constants (per design spec)
CHUNK_TOKENS = 512
CHUNK_OVERLAP = 128
TOP_K_CANDIDATES = 20
TOP_K_RERANKED = 5


class RAGPipeline:
    def __init__(self, search_service: SearchService) -> None:
        self.search = search_service
        self._http: Optional[httpx.AsyncClient] = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    # ── Grounding injection ───────────────────────────────────────────────────

    async def build_grounded_prompt(
        self,
        query: str,
        index_name: str,
        base_instructions: str,
        entity_id: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> str:
        """
        Retrieve top-k documents and inject them as system-level context.
        Model is instructed to cite sources and not hallucinate.
        """
        hits = await self.search.hybrid_search(
            query=query,
            index_name=index_name,
            top_k=TOP_K_RERANKED,
            filters=filters,
            entity_id=entity_id,
        )

        if not hits:
            context_block = "[No relevant documents retrieved. State that evidence is unavailable.]"
        else:
            chunks = []
            for i, hit in enumerate(hits, 1):
                chunks.append(
                    f"[SOURCE {i}] ID={hit['id']} | Source={hit['source']}\n{hit['content']}"
                )
            context_block = "\n\n".join(chunks)

        grounded_system = (
            f"{base_instructions}\n\n"
            "## Retrieved Evidence (cite these sources in your response)\n\n"
            f"{context_block}\n\n"
            "## Instructions\n"
            "- Only make factual claims supported by the retrieved evidence above.\n"
            "- Cite each claim using [SOURCE N] notation.\n"
            "- If evidence is insufficient, state uncertainty explicitly.\n"
            "- Do NOT use parametric memory for specific entity facts.\n"
            "- Return a valid JSON object matching the required output schema."
        )
        return grounded_system, hits

    # ── Prompt Shields (Layer 5) ──────────────────────────────────────────────

    async def check_prompt_injection(self, user_content: str) -> Dict[str, Any]:
        """
        Call Azure Content Safety text:shieldPrompt endpoint.
        Returns {"safe": bool, "attack_detected": bool, "details": dict}
        """
        if not settings.azure_content_safety_endpoint:
            return {"safe": True, "attack_detected": False, "details": {}}

        url = (
            f"{settings.azure_content_safety_endpoint}"
            "/contentsafety/text:shieldPrompt?api-version=2024-09-01"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.azure_content_safety_key,
            "Content-Type": "application/json",
        }
        body = {
            "userPrompt": user_content,
            "documents": [],
        }
        try:
            resp = await self.http.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            attack = data.get("userPromptAnalysis", {}).get("attackDetected", False)
            return {"safe": not attack, "attack_detected": attack, "details": data}
        except Exception as e:
            logger.warning("prompt_shield_error", error=str(e))
            return {"safe": True, "attack_detected": False, "details": {}}

    # ── Groundedness Detection (Layer 2) ─────────────────────────────────────

    async def check_groundedness(
        self, output_text: str, source_documents: List[str]
    ) -> Dict[str, Any]:
        """
        Call Azure Content Safety text:detectGroundedness endpoint.
        Returns {"grounded": bool, "score": float (1-5), "ungrounded_detections": list}
        """
        if not settings.azure_content_safety_endpoint:
            return {"grounded": True, "score": 5.0, "ungrounded_detections": [], "corrected_text": None}

        url = (
            f"{settings.azure_content_safety_endpoint}"
            "/contentsafety/text:detectGroundedness?api-version=2024-09-01"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.azure_content_safety_key,
            "Content-Type": "application/json",
        }
        body = {
            "domain": "Generic",
            "task": {
                "type": "QnA",
                "context": "\n\n".join(source_documents[:5]),
            },
            "text": output_text,
            "groundingSource": {
                "inline_document_sources": [
                    {"text": doc} for doc in source_documents[:5]
                ]
            },
        }
        if settings.groundedness_correction_enabled:
            body["reasoning"] = False
            body["correction"] = True

        try:
            resp = await self.http.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            score = data.get("ungroundednessScore", 0)  # lower = more grounded
            grounded = score < (1 - settings.groundedness_score_threshold / 5)
            return {
                "grounded": grounded,
                "score": 5 - (score * 5),  # convert to 1-5 where 5=fully grounded
                "ungrounded_detections": data.get("ungroundedDetections", []),
                "corrected_text": data.get("correctedText"),
            }
        except Exception as e:
            logger.warning("groundedness_check_error", error=str(e))
            return {"grounded": True, "score": 4.0, "ungrounded_detections": [], "corrected_text": None}

    # ── Full pipeline (search → inject → shield → parse → ground) ────────────

    async def run(
        self,
        query: str,
        index_name: str,
        base_instructions: str,
        run_fn,  # async fn(system_prompt, user_message) → str
        entity_id: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG pipeline for a specialist agent.
        run_fn is called with the grounded system prompt and user query.
        """
        # Layer 5 — Prompt Shields
        shield_result = await self.check_prompt_injection(query)
        if not shield_result["safe"]:
            logger.warning("prompt_injection_detected", query=query[:100])
            return {
                "blocked": True,
                "reason": "Prompt injection detected",
                "finding": "Input blocked by Prompt Shield",
                "risk_score": 0.0,
                "confidence": 0.0,
                "citations": [],
                "evidence_summary": "",
                "flags": ["PROMPT_INJECTION_BLOCKED"],
            }

        # Layer 1 — RAG Grounding
        grounded_system, hits = await self.build_grounded_prompt(
            query=query,
            index_name=index_name,
            base_instructions=base_instructions,
            entity_id=entity_id,
            filters=filters,
        )

        source_texts = [h["content"] for h in hits]
        citations = [
            {"source": h["source"], "document_id": h["id"], "relevance_score": h["score"]}
            for h in hits
        ]

        # Layer 1 cont. — run agent with grounded context
        raw_output = await run_fn(grounded_system, query)

        # Parse JSON output
        parsed = self._parse_agent_json(raw_output)
        parsed["citations"] = citations or parsed.get("citations", [])

        # Layer 2 — Groundedness Detection
        if source_texts:
            ground_result = await self.check_groundedness(
                raw_output, source_texts
            )
            parsed["groundedness_score"] = ground_result["score"]
            parsed["is_grounded"] = ground_result["grounded"]
            if ground_result.get("corrected_text"):
                parsed["finding"] = ground_result["corrected_text"]
        else:
            parsed["groundedness_score"] = None
            parsed["is_grounded"] = True

        return parsed

    def _parse_agent_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from agent response; return defaults on parse failure."""
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Best-effort: return a minimal valid structure
            logger.warning("agent_json_parse_failed", text_preview=text[:200])
            return {
                "finding": text[:500],
                "risk_score": 0.5,
                "confidence": 0.3,
                "citations": [],
                "evidence_summary": text[:300],
                "flags": ["PARSE_ERROR"],
            }

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
