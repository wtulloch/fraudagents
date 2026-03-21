"""
scripts/setup_foundry_agents.py
--------------------------------
Idempotently creates all 7 specialist agents in Azure AI Foundry using the
Microsoft Agent Framework (MAF) SDK (azure-ai-agents).

Usage:
    python -m scripts.setup_foundry_agents [--dry-run] [--force-recreate]

Prerequisites:
    • .env is populated with AZURE_AI_FOUNDRY_PROJECT_ENDPOINT + model names
    • az login (or AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID env vars)
"""

from __future__ import annotations

import argparse
import sys
import os

# Allow running from repo root: python -m scripts.setup_foundry_agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder
from azure.identity import DefaultAzureCredential

from backend.config import settings

# ── Agent definitions ─────────────────────────────────────────────────────────
AGENTS_TO_CREATE = [
    {
        "name": "adverse-media-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Adverse Media Agent in a financial crime detection system. "
            "Your role is to assess reputational risk for a given subject by analysing "
            "retrieved news articles, PEP (Politically Exposed Person) lists, and sanctions feeds. "
            "Always ground every finding in retrieved evidence. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[]}."
        ),
        "description": "Screens subjects against adverse news, PEP lists, and sanctions feeds.",
    },
    {
        "name": "transaction-pattern-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Transaction Pattern Agent. Analyse transaction data for behavioural "
            "anomalies: velocity spikes, structuring (sub-CTR splitting), layering, round-dollar "
            "patterns, and peer-group deviation. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[]}."
        ),
        "description": "Detects structuring, layering, velocity anomalies in transaction data.",
    },
    {
        "name": "kyc-kyb-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the KYC/KYB Lookup Agent. Perform entity resolution against CIF data "
            "and external registries. Build beneficial ownership chains, flag UBO gaps, "
            "dormant-entity reactivation, and high-risk jurisdiction exposure. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[]}."
        ),
        "description": "Resolves entity identity and builds beneficial ownership chains.",
    },
    {
        "name": "sanctions-matching-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Sanctions Matching Agent. Perform fuzzy name matching "
            "(Jaro-Winkler, phonetic, transliteration) against OFAC, EU, UN, and HMT watchlists. "
            "Always report match_confidence alongside the finding. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[], match_confidence}."
        ),
        "description": "Performs watchlist screening against OFAC/EU/UN/HMT sanctions lists.",
    },
    {
        "name": "fraud-agent",
        "model": settings.model_o3_mini,
        "instructions": (
            "You are the Fraud Detection Agent. Use multi-step reasoning to identify "
            "account takeover, synthetic identity, first-party fraud, payment fraud, and card fraud. "
            "Consider device, geo-location, and behavioural signals. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[]}."
        ),
        "description": "Detects account takeover, synthetic identity, payment fraud patterns.",
    },
    {
        "name": "aml-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the Anti-Money Laundering (AML) Agent. Detect placement, layering, and "
            "integration typologies. Identify trade-based money laundering (TBML), PEP activity, "
            "high-risk jurisdictions, and sanctions evasion. "
            "Return ONLY valid JSON: {finding, risk_score, confidence, citations[], "
            "evidence_summary, flags[]}."
        ),
        "description": "Detects AML typologies: placement, layering, PEP, trade-based ML.",
    },
    {
        "name": "sar-drafting-agent",
        "model": settings.model_gpt4o,
        "instructions": (
            "You are the SAR Drafting Agent. Synthesise investigation findings from all "
            "specialist agents into a FinCEN-compliant Suspicious Activity Report narrative. "
            "Structure: Subject Description → Activity Description → Why Suspicious → "
            "Supporting Evidence. Always cite specific transactions and dates. "
            "Return ONLY valid JSON: {narrative_text, subject_description, "
            "activity_description, why_suspicious, supporting_evidence[]}."
        ),
        "description": "Drafts FinCEN-compliant SAR narratives from investigation findings.",
    },
]


def setup_agents(dry_run: bool = False, force_recreate: bool = False) -> None:
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Setting up Foundry agents…")
    print(f"Endpoint: {settings.azure_ai_foundry_project_endpoint}\n")

    credential = DefaultAzureCredential()
    client = AgentsClient(
        endpoint=settings.azure_ai_foundry_project_endpoint,
        credential=credential,
    )

    # Fetch existing agents
    existing: dict[str, str] = {}  # name → id
    try:
        pages = client.list_agents(order=ListSortOrder.DESCENDING)
        for agent in pages:
            existing[agent.name] = agent.id
        print(f"Found {len(existing)} existing agents in Foundry.\n")
    except Exception as exc:
        print(f"Warning: Could not list existing agents: {exc}")

    results = []
    for spec in AGENTS_TO_CREATE:
        name = spec["name"]
        print(f"  → {name}  (model: {spec['model']})")

        if name in existing and not force_recreate:
            print(f"     ✓ Already exists [id={existing[name][:12]}…] — skipped.\n")
            results.append({"name": name, "id": existing[name], "action": "skipped"})
            continue

        if dry_run:
            print(f"     [DRY RUN] Would create agent.\n")
            results.append({"name": name, "id": None, "action": "dry_run"})
            continue

        # Delete old version if force-recreating
        if name in existing and force_recreate:
            try:
                client.delete_agent(existing[name])
                print(f"     Deleted old agent [{existing[name][:12]}…]")
            except Exception as exc:
                print(f"     Warning: Could not delete old agent: {exc}")

        try:
            agent = client.create_agent(
                model=spec["model"],
                name=spec["name"],
                instructions=spec["instructions"],
                description=spec.get("description", ""),
            )
            print(f"     ✓ Created [id={agent.id[:12]}…]\n")
            results.append({"name": name, "id": agent.id, "action": "created"})
        except Exception as exc:
            print(f"     ✗ FAILED: {exc}\n")
            results.append({"name": name, "id": None, "action": "error", "error": str(exc)})

    # Summary
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    for r in results:
        status = "✓" if r["action"] in ("created", "skipped") else ("~" if r["action"] == "dry_run" else "✗")
        print(f"  {status}  {r['name']:40s}  [{r['action'].upper()}]")

    errors = [r for r in results if r["action"] == "error"]
    if errors:
        print(f"\n{len(errors)} agent(s) failed to create. Check the errors above.")
        sys.exit(1)
    else:
        print(f"\nAll {len(AGENTS_TO_CREATE)} agents configured successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Azure AI Foundry agents for the Fraud Detection System."
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating.")
    parser.add_argument("--force-recreate", action="store_true", help="Delete and recreate existing agents.")
    args = parser.parse_args()
    setup_agents(dry_run=args.dry_run, force_recreate=args.force_recreate)


if __name__ == "__main__":
    main()
