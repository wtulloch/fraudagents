"""Agent management routes — list/inspect Foundry agents and model router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.services.model_router import model_router

router = APIRouter()


@router.get("/")
async def list_agents(request: Request):
    """List all registered Foundry agents and their cached IDs."""
    foundry = request.app.state.foundry
    return {
        "registered_agents": list(foundry._agent_id_cache.keys()),
        "agent_ids": foundry._agent_id_cache,
    }


@router.get("/model-router")
async def get_model_routes():
    """Return the task → model routing table."""
    return model_router.all_routes()


@router.post("/reload")
async def reload_agents(request: Request):
    """Re-register all agents in Foundry (useful after config changes)."""
    foundry = request.app.state.foundry
    await foundry.ensure_agents()
    return {"reloaded": list(foundry._agent_id_cache.keys())}
