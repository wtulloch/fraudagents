"""
Azure AI Search service — hybrid retrieval (BM25 + vector) with semantic reranker.

Four domain indexes:
  • transactions-index  — transaction records + behavioural patterns
  • kyc-index           — KYC/KYB entity data, UBO chains
  • media-index         — adverse media corpus
  • sanctions-index     — OFAC, EU, UN, HMT watchlists
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import structlog
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI

from backend.config import settings

logger = structlog.get_logger(__name__)

# ── Index schema helpers ──────────────────────────────────────────────────────

def _base_fields() -> List[SearchField]:
    """Shared fields across all domain indexes."""
    return [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="entity_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="jurisdiction", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="date_range_start", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="date_range_end", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="metadata_json", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,  # text-embedding-ada-002
            vector_search_profile_name="hnsw-profile",
        ),
    ]


def _build_index(name: str, extra_fields: Optional[List[SearchField]] = None) -> SearchIndex:
    fields = _base_fields() + (extra_fields or [])
    return SearchIndex(
        name=name,
        fields=fields,
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
        ),
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="content")],
                        title_field=SemanticField(field_name="title"),
                    ),
                )
            ]
        ),
    )


INDEX_DEFINITIONS = {
    settings.azure_search_transactions_index: _build_index(
        settings.azure_search_transactions_index,
        [
            SimpleField(name="account_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="amount", type=SearchFieldDataType.Double, filterable=True),
            SimpleField(name="channel", type=SearchFieldDataType.String, filterable=True),
        ],
    ),
    settings.azure_search_kyc_index: _build_index(
        settings.azure_search_kyc_index,
        [
            SimpleField(name="customer_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="customer_type", type=SearchFieldDataType.String, filterable=True),
        ],
    ),
    settings.azure_search_media_index: _build_index(
        settings.azure_search_media_index,
        [
            SimpleField(name="risk_category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="publication_date", type=SearchFieldDataType.String, filterable=True),
        ],
    ),
    settings.azure_search_sanctions_index: _build_index(
        settings.azure_search_sanctions_index,
        [
            SimpleField(name="list_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="match_score", type=SearchFieldDataType.Double, filterable=True),
        ],
    ),
}


class SearchService:
    def __init__(self) -> None:
        self._credential = AzureKeyCredential(settings.azure_search_api_key)
        self._index_client: Optional[SearchIndexClient] = None
        self._search_clients: Dict[str, SearchClient] = {}
        self._openai: Optional[AsyncAzureOpenAI] = None

    @property
    def index_client(self) -> SearchIndexClient:
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=settings.azure_search_endpoint,
                credential=self._credential,
            )
        return self._index_client

    def _get_search_client(self, index_name: str) -> SearchClient:
        if index_name not in self._search_clients:
            self._search_clients[index_name] = SearchClient(
                endpoint=settings.azure_search_endpoint,
                index_name=index_name,
                credential=self._credential,
            )
        return self._search_clients[index_name]

    @property
    def openai_client(self) -> AsyncAzureOpenAI:
        if self._openai is None:
            self._openai = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        return self._openai

    # ── Init ──────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        """Create indexes if they do not already exist."""
        for index_name, index_def in INDEX_DEFINITIONS.items():
            try:
                await self.index_client.create_or_update_index(index_def)
                logger.info("search_index_ready", index=index_name)
            except Exception as e:
                logger.warning("search_index_warning", index=index_name, error=str(e))

    # ── Embedding ─────────────────────────────────────────────────────────────

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding using the configured embedding deployment."""
        response = await self.openai_client.embeddings.create(
            model=settings.model_embedding,
            input=text,
        )
        return response.data[0].embedding

    # ── Hybrid search ─────────────────────────────────────────────────────────

    async def hybrid_search(
        self,
        query: str,
        index_name: str,
        top_k: int = 5,
        filters: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: BM25 keyword + vector similarity, semantically reranked.
        top-k=20 candidates reranked to top-k=5 (per design spec).
        """
        t0 = time.monotonic()
        embedding = await self.generate_embedding(query)
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=20,
            fields="content_vector",
        )

        search_client = self._get_search_client(index_name)
        filter_str = filters
        if entity_id and not filter_str:
            filter_str = f"entity_id eq '{entity_id}'"
        elif entity_id and filter_str:
            filter_str = f"({filter_str}) and entity_id eq '{entity_id}'"

        results = await search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["id", "content", "title", "source", "entity_id", "metadata_json"],
            top=top_k,
            filter=filter_str,
            query_type="semantic",
            semantic_configuration_name="semantic-config",
        )

        hits = []
        async for r in results:
            meta = {}
            if r.get("metadata_json"):
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass
            hits.append(
                {
                    "id": r["id"],
                    "content": r.get("content", ""),
                    "title": r.get("title", ""),
                    "source": r.get("source", ""),
                    "entity_id": r.get("entity_id", ""),
                    "score": r.get("@search.score", 0),
                    "reranker_score": r.get("@search.reranker_score"),
                    "metadata": meta,
                }
            )

        elapsed = int((time.monotonic() - t0) * 1000)
        logger.debug("hybrid_search_done", index=index_name, hits=len(hits), latency_ms=elapsed)
        return hits

    # ── Index documents ───────────────────────────────────────────────────────

    async def index_documents(
        self, index_name: str, documents: List[Dict[str, Any]]
    ) -> None:
        """Upsert documents including pre-computed content_vector."""
        # Only these fields are declared in the shared index schema.
        # Extra fields from source records (e.g. 'name', 'verified') are stripped
        # here so Azure AI Search never receives an undeclared field.
        ALLOWED_FIELDS = {
            "id", "content", "title", "source", "entity_id",
            "jurisdiction", "date_range_start", "date_range_end",
            "metadata_json", "content_vector",
        }

        search_client = self._get_search_client(index_name)
        clean_docs: List[Dict[str, Any]] = []
        for doc in documents:
            # Generate embedding before projecting so we still use content
            if "content_vector" not in doc and "content" in doc:
                doc["content_vector"] = await self.generate_embedding(doc["content"])
            if "metadata_json" not in doc and "metadata" in doc:
                doc["metadata_json"] = json.dumps(doc.pop("metadata"))
            clean_docs.append({k: v for k, v in doc.items() if k in ALLOWED_FIELDS})

        result = await search_client.upload_documents(clean_docs)
        succeeded = sum(1 for r in result if r.succeeded)
        logger.info("documents_indexed", index=index_name, succeeded=succeeded, total=len(clean_docs))

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._index_client:
            await self._index_client.close()
        for client in self._search_clients.values():
            await client.close()
        if self._openai:
            await self._openai.close()
