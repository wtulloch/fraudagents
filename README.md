# Fraud Detection System — Multi-Agent Platform

An end-to-end autonomous fraud and AML detection system built on **Azure AI Foundry** using the **Microsoft Agent Framework (MAF)**. Implements a fan-out / fan-in orchestration pattern with Human-in-the-Loop governance, RAG-grounded agents, and a reinforcement learning feedback loop.

---

## Architecture Overview

```
Business / Event Trigger
        │
  Alert Router (MAF)
        │
  ┌─────┼──────────────────────────────────┐  FAN-OUT
  │     │                                  │
  ▼     ▼          ▼              ▼         ▼
Adverse  Transaction  KYC/KYB  Sanctions  Fraud / AML
Media    Pattern      Lookup   Matching   Agents
Agent    Agent        Agent    Agent
  │     │          │              │         │
  └─────┴──────────┴──────────────┴─────────┘  FAN-IN
                    │
             Risk Aggregator
                    │
             Decision Gate
             (SAR / Escalate / Close)
```

### Key Capabilities
- **Fan-out / Fan-in**: All specialist agents run in parallel via asyncio
- **RAG Grounding**: Azure AI Search (hybrid BM25 + vector) per domain index
- **5-Layer Hallucination Prevention**: RAG → Groundedness → Active Correction → Deterministic Gates → Prompt Shields
- **Human-in-the-Loop (HITL)**: PEP, high-value, and SWIFT cases always require human review
- **Reinforcement Learning Feedback**: Analyst feedback stored in Cosmos DB, driving model improvement
- **Full Audit Trail**: Every agent step logged with data sources, reasoning, and decision rationale
- **Synthetic Data Generator**: Built-in UI and API for realistic test data

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Models & Agents** | Azure AI Foundry (MAF), GPT-4o, GPT-4o-mini, o3-mini |
| **Orchestration** | Microsoft Agent Framework (MAF) — `azure-ai-agents` SDK |
| **Vector Search** | Azure AI Search (hybrid retrieval, semantic reranker) |
| **Session Store** | Azure Cosmos DB (NoSQL) |
| **Hallucination Guard** | Azure Content Safety (Prompt Shields + Groundedness) |
| **Backend** | Python 3.11+, FastAPI, asyncio |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS, Recharts |

---

## Project Structure

```
fraudagents/
├── backend/
│   ├── main.py                     # FastAPI entry point
│   ├── config.py                   # Pydantic settings from .env
│   ├── api/routes/                 # REST API endpoints
│   ├── agents/
│   │   ├── orchestrator.py         # Fan-out/fan-in orchestrator
│   │   ├── alert_router.py         # Alert context builder
│   │   ├── risk_aggregator.py      # Unified risk scoring
│   │   ├── decision_gate.py        # Deterministic SAR/Escalate/Close
│   │   └── specialist/             # Domain-specific agents (MAF)
│   ├── services/
│   │   ├── foundry_service.py      # MAF agent lifecycle
│   │   ├── search_service.py       # Azure AI Search RAG
│   │   ├── cosmos_service.py       # Session + audit store
│   │   ├── model_router.py         # Task-to-model routing
│   │   └── synthetic_data_service.py
│   ├── models/                     # Pydantic schemas
│   └── utils/                      # Audit, HITL, hallucination guard
├── frontend/
│   └── src/
│       ├── pages/                  # Dashboard, Alerts, Cases, SAR, HITL
│       ├── components/             # Reusable UI components
│       ├── hooks/                  # React Query + WebSocket hooks
│       └── services/api.ts         # Typed API client
├── scripts/
│   ├── setup_foundry_agents.py     # Create agents in Foundry via MAF
│   ├── create_search_indexes.py    # Provision AI Search indexes
│   └── generate_synthetic_data.py # Seed test data
└── locustfile.py                   # Load testing
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd fraudagents
cp .env.example .env
# Edit .env with your Azure credentials
```

### 2. Backend setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 3. Provision Azure resources

```bash
# Create AI Search indexes
python scripts/create_search_indexes.py

# Create Foundry agents via MAF
python scripts/setup_foundry_agents.py

# Seed synthetic data
python scripts/generate_synthetic_data.py --records 500
```

### 4. Start backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### 6. Load test

```bash
locust -f locustfile.py -u 10 -r 2 --run-time 1m
```

---

## Agent Descriptions

| Agent | Model | Role |
|---|---|---|
| **Adverse Media Agent** | GPT-4o | Queries news APIs, PEP lists, sanctions feeds via RAG |
| **Transaction Pattern Agent** | GPT-4o | Velocity, structuring, peer-group deviation analysis |
| **KYC/KYB Lookup Agent** | GPT-4o | Entity resolution, beneficial ownership, UBO gaps |
| **Sanctions Matching Agent** | GPT-4o | Fuzzy name matching against OFAC/EU/UN/HMT lists |
| **Fraud Agent** | o3-mini | Multi-step chain-of-thought for novel fraud patterns |
| **AML Agent** | GPT-4o | Layering, placement, integration pattern detection |

---

## Human-in-the-Loop Governance

| Tier | Automation | Trigger |
|---|---|---|
| **Tier 1 — Alert Triage** | High (60-80%) | Low-risk: auto-closed with 2+ agent consensus |
| **Tier 2 — Case Investigation** | Agent-assisted | Medium-risk: analyst reviews pre-built evidence package |
| **Tier 3 — SAR Filing** | Human sign-off required | SAR narratives drafted by agent, approved by compliance |

---

## Environment Variables

See `.env.example` for the full list of required configuration keys.
