---
title: Project Agent Guidelines
description: Repository guidance for coding agents working on the fraud and AML detection platform.
---

## Project overview

This project combines a Python 3.11+ FastAPI backend with a React 18,
TypeScript, Vite, and Tailwind CSS frontend. Investigations use Azure AI
Foundry agents, Azure AI Search retrieval, and Azure Cosmos DB persistence.
See [README.md](README.md) for architecture and feature context.

## Repository map

* [backend/main.py](backend/main.py): FastAPI entry point and service lifecycle
* [backend/config.py](backend/config.py): Pydantic settings and environment configuration
* [backend/api/routes](backend/api/routes): REST and WebSocket endpoints
* [backend/agents](backend/agents): Fan-out/fan-in orchestration, specialists, risk aggregation, and decision gates
* [backend/models](backend/models): Pydantic API and persistence schemas
* [backend/services](backend/services): Azure integrations and synthetic data generation
* [backend/utils](backend/utils): Audit, human-in-the-loop (HITL), and hallucination safeguards
* [frontend/src](frontend/src): Pages, components, hooks, and shared TypeScript types
* [frontend/src/services/api.ts](frontend/src/services/api.ts): Frontend API client
* [scripts](scripts): Provisioning and synthetic data utilities
* [locustfile.py](locustfile.py): Integration and load scenarios

## Local development

Run these PowerShell commands from the repository root. Create the environment
file only if it does not already exist, then configure it using
[.env.example](.env.example). Never overwrite an existing local configuration.
Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first.

```powershell
Copy-Item .env.example .env
uv sync --locked
Set-Location frontend
npm ci
```

Start the backend from the repository root:

```powershell
uv run --locked python -m uvicorn backend.main:app --reload --port 8000
```

Use [pyproject.toml](pyproject.toml) as the Python dependency source and keep
[uv.lock](uv.lock) in version control. Use `uv add` and `uv remove` to change
dependencies, and `uv run --locked` for Python commands. Do not manage the
environment with pip or edit the generated lockfile manually.

In a separate terminal, run `npm run dev` from the frontend directory.
The UI runs at <http://localhost:5173> and proxies `/api` to port 8000.
API documentation is at <http://localhost:8000/api/docs>.

Backend startup is not an offline smoke test: it initializes Cosmos DB
containers, Search indexes, and Foundry agents. Confirm the Azure environment
and authorization before starting it.

## Change conventions

* Keep routes focused on HTTP concerns; place integrations in services and investigation logic in agents.
* Follow existing async Python, Pydantic validation, and `structlog` patterns. Keep configuration in settings rather than hard-coded values.
* Keep backend schemas, frontend types, API calls, and React Query cache invalidation aligned when changing contracts.
* Preserve deterministic decision gates, HITL overrides, SAR approval requirements, evidence citations, and audit trails. Do not replace these controls with model-only decisions.
* Preserve Cosmos DB partition-key conventions when changing persistence operations.
* Surface failures through existing logging and API error patterns; do not hide failed investigations behind successful-looking defaults.
* Make focused changes and update directly affected documentation. Do not modify generated output or unrelated code.

## Validation

* Run `npm run build` from the frontend directory for UI changes; it runs TypeScript checking and a Vite production build.
* `npm run lint` is declared, but no ESLint configuration is checked in. Report configuration failures rather than claiming lint passes.
* No automated unit-test suite or backend lint configuration is currently checked in. Add focused regression tests for behavior changes and document how to run them.
* Use mocks or fakes for Azure and model calls in unit tests. Do not require live credentials for isolated tests.
* Treat Locust runs as integration/load tests, not unit tests: they require a configured backend, can create data, and incur Azure usage.
* Report the checks actually run and any skipped checks or environment limitations. Documentation-only changes do not require application builds.

## Data and operational safety

* Never commit credentials, connection strings, local environment files, or real customer and transaction data. Use synthetic or de-identified fixtures.
* Do not log secrets or unnecessary personal information in prompts, traces, or audit records.
* Do not provision, delete, recreate, or seed cloud resources without explicit authorization. Inspect script flags before execution; recreation options can delete resources.
* Do not treat `/health` as proof that downstream services are ready, or SAR persistence as a real regulatory filing.
