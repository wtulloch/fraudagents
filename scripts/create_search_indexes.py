"""
scripts/create_search_indexes.py
---------------------------------
Creates (or recreates) the four Azure AI Search indexes used by the RAG pipeline:
  • transactions-index   — transaction records + behavioural patterns
  • kyc-index            — KYC/KYB entity data, UBO chains
  • media-index          — adverse media articles
  • sanctions-index      — OFAC / EU / UN / HMT watchlists

Usage:
    python -m scripts.create_search_indexes [--recreate] [--index INDEXNAME]

Prerequisites:
    • .env is populated with AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY
"""

from __future__ import annotations

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient
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

from backend.config import settings

EMBEDDING_DIMS = 3072  # text-embedding-3-large


def _shared_fields() -> list[SearchField]:
    return [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="entity_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="jurisdiction", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="date_range_start", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SimpleField(name="date_range_end", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        SearchableField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
        SearchableField(name="metadata_json", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMS,
            vector_search_profile_name="hnsw-profile",
        ),
    ]


def _vector_search() -> VectorSearch:
    return VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config", parameters={"m": 4, "efConstruction": 400})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-config")],
    )


def _semantic_search(config_name: str) -> SemanticSearch:
    return SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=config_name,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="tags")],
                ),
            )
        ]
    )


# ── Per-index extra fields ────────────────────────────────────────────────────
def _transaction_extra_fields() -> list[SearchField]:
    return [
        SimpleField(name="account_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="amount", type=SearchFieldDataType.Double, filterable=True, sortable=True),
        SimpleField(name="currency", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="typology_label", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="is_fraud", type=SearchFieldDataType.Boolean, filterable=True),
        SimpleField(name="risk_score", type=SearchFieldDataType.Double, filterable=True, sortable=True),
    ]


def _kyc_extra_fields() -> list[SearchField]:
    return [
        SimpleField(name="customer_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="entity_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="risk_rating", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="pep_flag", type=SearchFieldDataType.Boolean, filterable=True),
        SimpleField(name="kyc_status", type=SearchFieldDataType.String, filterable=True, facetable=True),
    ]


def _media_extra_fields() -> list[SearchField]:
    return [
        SearchableField(name="subject_name", type=SearchFieldDataType.String),
        SimpleField(name="sentiment", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="article_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="credibility_score", type=SearchFieldDataType.Double, sortable=True),
    ]


def _sanctions_extra_fields() -> list[SearchField]:
    return [
        SearchableField(name="listed_name", type=SearchFieldDataType.String),
        SearchableField(name="aliases", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
        SimpleField(name="list_type", type=SearchFieldDataType.String, filterable=True, facetable=True),  # OFAC/EU/UN/HMT
        SimpleField(name="program", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="active", type=SearchFieldDataType.Boolean, filterable=True),
        SimpleField(name="match_score_threshold", type=SearchFieldDataType.Double),
    ]


INDEX_SPECS = [
    {
        "name": settings.azure_search_transactions_index,
        "semantic_config": "txn-semantic",
        "extra_fields": _transaction_extra_fields,
        "description": "Transaction records and behavioural pattern embeddings",
    },
    {
        "name": settings.azure_search_kyc_index,
        "semantic_config": "kyc-semantic",
        "extra_fields": _kyc_extra_fields,
        "description": "KYC/KYB entity data and UBO chains",
    },
    {
        "name": settings.azure_search_media_index,
        "semantic_config": "media-semantic",
        "extra_fields": _media_extra_fields,
        "description": "Adverse media articles and news corpus",
    },
    {
        "name": settings.azure_search_sanctions_index,
        "semantic_config": "sanctions-semantic",
        "extra_fields": _sanctions_extra_fields,
        "description": "OFAC / EU / UN / HMT watchlist entries",
    },
]


def create_indexes(recreate: bool = False, target_index: str | None = None) -> None:
    endpoint = settings.azure_search_endpoint
    key = settings.azure_search_api_key
    print(f"\nAzure AI Search endpoint: {endpoint}\n")

    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    for spec in INDEX_SPECS:
        index_name = spec["name"]
        if target_index and index_name != target_index:
            continue

        print(f"  → {index_name}  ({spec['description']})")

        # Check / delete existing
        if recreate:
            try:
                client.delete_index(index_name)
                print(f"     Deleted existing index.")
            except ResourceNotFoundError:
                pass

        fields = _shared_fields() + spec["extra_fields"]()
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=_vector_search(),
            semantic_search=_semantic_search(spec["semantic_config"]),
        )

        try:
            result = client.create_or_update_index(index)
            print(f"     ✓ Index '{result.name}' ready — {len(result.fields)} fields.\n")
        except Exception as exc:
            print(f"     ✗ FAILED: {exc}\n")
            sys.exit(1)

    print("All indexes created/updated successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Azure AI Search indexes for the Fraud Detection System."
    )
    parser.add_argument("--recreate", action="store_true",
                        help="Delete and recreate each index (loses all indexed data).")
    parser.add_argument("--index", metavar="NAME",
                        help="Only create/update a single named index.")
    args = parser.parse_args()
    create_indexes(recreate=args.recreate, target_index=args.index)


if __name__ == "__main__":
    main()
