"""Synthetic data generation routes."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.services.synthetic_data_service import SyntheticDataService

router = APIRouter()


class GenerateRequest(BaseModel):
    n_records: int = 100
    fraud_rate: float = 0.15
    index_to_search: bool = True  # also push to AI Search


@router.post("/generate")
async def generate_data(request: Request, body: GenerateRequest):
    search = request.app.state.search
    cosmos = request.app.state.cosmos

    svc = SyntheticDataService()
    batch = svc.generate_batch(n_records=body.n_records, fraud_rate=body.fraud_rate)

    # Index into AI Search if requested
    if body.index_to_search:
        from backend.config import settings

        # Index KYC records
        kyc_docs = [
            {**r, "content": r.get("content", ""), "title": r.get("title", "KYC Record")}
            for r in batch["kyc_records"]
        ]
        await search.index_documents(settings.azure_search_kyc_index, kyc_docs)

        # Index media articles
        media_docs = [
            {**r, "content": r.get("content", ""), "title": r.get("title", "Media Article")}
            for r in batch["media_articles"]
        ]
        if media_docs:
            await search.index_documents(settings.azure_search_media_index, media_docs)

        # Index sanctions
        sanctions_docs = [
            {**r, "content": r.get("content", ""), "title": r.get("title", "Sanctions Entry")}
            for r in batch["sanctions_entries"]
        ]
        await search.index_documents(settings.azure_search_sanctions_index, sanctions_docs)

    # Save alerts to Cosmos
    alert_count = 0
    for alert in batch["alerts"]:
        await cosmos.save_alert(alert)
        alert_count += 1

    # Persist batch metadata
    batch_meta = {
        "id": batch["batch_id"],
        "batch_id": batch["batch_id"],
        "generated_at": batch["generated_at"],
        "counts": batch["counts"],
        "n_records": body.n_records,
        "fraud_rate": body.fraud_rate,
        "indexed": body.index_to_search,
    }
    await cosmos.upsert("synthetic_batches", batch_meta)

    return {
        "batch_id": batch["batch_id"],
        "counts": batch["counts"],
        "alerts_saved_to_cosmos": alert_count,
        "indexed_to_search": body.index_to_search,
    }


@router.get("/batches")
async def list_batches(request: Request):
    cosmos = request.app.state.cosmos
    return await cosmos.query(
        "synthetic_batches",
        "SELECT * FROM c ORDER BY c.generated_at DESC OFFSET 0 LIMIT 20",
        [],
    )


@router.get("/scenario/{typology}")
async def generate_scenario(typology: str, n_transactions: int = 10):
    """Generate a single alert scenario for a given typology."""
    svc = SyntheticDataService()
    return svc.generate_alert_scenario(typology=typology, n_transactions=n_transactions)
