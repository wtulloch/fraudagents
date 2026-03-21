"""
FastAPI application entry-point.

Lifecycle:
  startup  → init Cosmos DB containers, AI Search indexes, Foundry agents
  shutdown → close all async clients
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.api.routes import (
    alerts,
    cases,
    agents,
    sar,
    dashboard,
    synthetic,
    feedback,
    hitl,
)
from backend.services.cosmos_service import CosmosService
from backend.services.search_service import SearchService
from backend.services.foundry_service import FoundryService

# ── Structured logging setup ──────────────────────────────────────────────────
logging.basicConfig(level=settings.log_level)
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.dev.ConsoleRenderer() if not settings.is_production
        else structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise and tear down shared Azure service clients."""
    logger.info("startup", environment=settings.environment)

    # Initialise services (they cache their clients internally)
    cosmos = CosmosService()
    await cosmos.ensure_containers()

    search = SearchService()
    await search.ensure_indexes()

    foundry = FoundryService()
    try:
        await foundry.ensure_agents()
    except Exception as exc:  # noqa: BLE001
        logger.warning("foundry_init_skipped", error=str(exc))

    # Attach to app state so routes can access them
    app.state.cosmos = cosmos
    app.state.search = search
    app.state.foundry = foundry

    logger.info("all services ready")
    yield

    logger.info("shutdown — closing clients")
    await cosmos.close()
    await search.close()
    await foundry.close()


app = FastAPI(
    title="Fraud Detection System — Multi-Agent API",
    version="1.0.0",
    description=(
        "End-to-end autonomous fraud & AML detection using Azure AI Foundry "
        "MAF agents with fan-out/fan-in orchestration, RAG grounding, and HITL governance."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(sar.router, prefix="/api/sar", tags=["SAR"])
app.include_router(hitl.router, prefix="/api/hitl", tags=["HITL"])
app.include_router(synthetic.router, prefix="/api/synthetic", tags=["Synthetic Data"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback / RL"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "environment": settings.environment}


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check logs for details."},
    )
