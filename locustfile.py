"""
locustfile.py — Fraud Detection System Load Test
-------------------------------------------------
Simulates realistic analyst and automated workflows:
  • Dashboard metrics polling
  • Alert list fetching
  • Full investigation pipeline (fan-out → fan-in)
  • SAR listing
  • HITL queue polling
  • Synthetic data generation

Target: 10 concurrent users, ramp 2 users/sec, 1-minute run
  locust -f locustfile.py -u 10 -r 2 --run-time 1m --headless --host http://localhost:8000

For live UI:
  locust -f locustfile.py --host http://localhost:8000
"""

from __future__ import annotations

import json
import random
import uuid

from locust import HttpUser, SequentialTaskSet, between, events, task


# ── Seed data: pre-created alert IDs (populated during test_start) ────────────
_alert_ids: list[str] = []
_account_ids: list[str] = []

TYPOLOGIES = [
    "STRUCTURING", "LAYERING", "WIRE_FRAUD", "CARD_FRAUD",
    "SANCTIONS_EVASION", "ADVERSE_MEDIA", "ACCOUNT_TAKEOVER",
    "SYNTHETIC_IDENTITY", "PAYMENT_FRAUD",
]


@events.test_start.add_listener
def seed_alerts(environment, **_kwargs):
    """Create a small pool of alerts before the main test begins."""
    base_url = environment.host or "http://localhost:8000"
    import requests

    print("\n[locust] Seeding test alerts…")
    for _ in range(20):
        account_id = str(uuid.uuid4())
        body = {
            "account_id": account_id,
            "customer_name": f"Test Customer {random.randint(1000, 9999)}",
            "typology": random.choice(TYPOLOGIES),
            "source": "locust-load-test",
            "amount": round(random.uniform(5_000, 500_000), 2),
            "currency": "USD",
            "description": "Automated load test alert",
            "transaction_ids": [str(uuid.uuid4()) for _ in range(3)],
            "priority": random.choice(["HIGH", "MEDIUM", "LOW"]),
        }
        try:
            resp = requests.post(f"{base_url}/api/alerts/", json=body, timeout=10)
            if resp.status_code == 201:
                data = resp.json()
                _alert_ids.append(data["id"])
                _account_ids.append(data["account_id"])
        except Exception as exc:
            print(f"  [seed] Failed to create alert: {exc}")

    print(f"[locust] Seeded {len(_alert_ids)} test alerts.\n")


# ── Task Sets ─────────────────────────────────────────────────────────────────

class AnalystDashboardTasks(SequentialTaskSet):
    """Simulates a compliance analyst reviewing the dashboard and alert queue."""

    @task
    def get_dashboard_metrics(self):
        self.client.get("/api/dashboard/metrics", name="GET /dashboard/metrics")

    @task
    def list_all_alerts(self):
        self.client.get("/api/alerts/?limit=50", name="GET /alerts (all)")

    @task
    def list_new_alerts(self):
        self.client.get("/api/alerts/?status=NEW&limit=25", name="GET /alerts (NEW)")

    @task
    def list_hitl_queue(self):
        self.client.get("/api/hitl/queue?resolved=false", name="GET /hitl/queue")

    @task
    def list_sars(self):
        self.client.get("/api/sar/", name="GET /sar")

    @task
    def list_cases(self):
        self.client.get("/api/cases/?limit=25", name="GET /cases")

    @task
    def get_model_router(self):
        self.client.get("/api/agents/model-router", name="GET /agents/model-router")

    @task
    def get_audit_trail(self):
        self.client.get("/api/dashboard/audit-trail?limit=20", name="GET /audit-trail")


class InvestigationPipelineTasks(SequentialTaskSet):
    """Simulates triggering the full agent investigation pipeline on an alert."""

    def on_start(self):
        self._alert_id = None
        self._account_id = None

    @task
    def pick_alert(self):
        """Fetch a NEW alert to investigate."""
        with self.client.get("/api/alerts/?status=NEW&limit=10",
                             name="GET /alerts (pick)", catch_response=True) as resp:
            if resp.status_code == 200:
                alerts = resp.json()
                if alerts:
                    chosen = random.choice(alerts)
                    self._alert_id = chosen.get("id")
                    self._account_id = chosen.get("account_id")
                    resp.success()
                else:
                    # No new alerts — create one on the fly
                    resp.success()
                    self._alert_id = None

    @task
    def trigger_investigation(self):
        """POST /alerts/{id}/investigate — kicks off the 6-agent fan-out pipeline."""
        if not self._alert_id:
            # Create a fresh alert to investigate
            account_id = str(uuid.uuid4())
            body = {
                "account_id": account_id,
                "customer_name": f"Locust Customer {random.randint(1, 9999)}",
                "typology": random.choice(TYPOLOGIES),
                "source": "locust-investigation",
                "amount": round(random.uniform(10_000, 250_000), 2),
                "currency": "USD",
                "description": "Load test investigation trigger",
                "transaction_ids": [str(uuid.uuid4())],
                "priority": "HIGH",
            }
            with self.client.post("/api/alerts/", json=body,
                                  name="POST /alerts (create)", catch_response=True) as r:
                if r.status_code == 201:
                    data = r.json()
                    self._alert_id = data["id"]
                    self._account_id = data["account_id"]

        if self._alert_id:
            payload = {"account_id": self._account_id, "session_id": str(uuid.uuid4())}
            with self.client.post(
                f"/api/alerts/{self._alert_id}/investigate",
                json=payload,
                name="POST /alerts/investigate",
                catch_response=True,
                timeout=120,
            ) as resp:
                if resp.status_code == 200:
                    result = resp.json()
                    if "decision" in result:
                        resp.success()
                    else:
                        resp.failure(f"Missing 'decision' in response: {resp.text[:200]}")
                elif resp.status_code in (404, 422):
                    resp.failure(f"HTTP {resp.status_code}: {resp.text[:100]}")
                else:
                    resp.failure(f"Unexpected status {resp.status_code}")

    @task
    def fetch_agent_runs(self):
        """GET /alerts/{id}/agent-runs — retrieve stored agent outputs."""
        if self._alert_id:
            self.client.get(
                f"/api/alerts/{self._alert_id}/agent-runs",
                name="GET /alerts/agent-runs",
            )


class SyntheticDataTasks(SequentialTaskSet):
    """Simulates synthetic data management (lighter weight)."""

    @task(3)
    def list_batches(self):
        self.client.get("/api/synthetic/batches", name="GET /synthetic/batches")

    @task(1)
    def generate_small_batch(self):
        body = {"n_records": 10, "fraud_rate": 0.20, "index_to_search": False}
        with self.client.post("/api/synthetic/generate", json=body,
                              name="POST /synthetic/generate (10rec)",
                              catch_response=True, timeout=60) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def get_scenario(self):
        typology = random.choice(["STRUCTURING", "CARD_FRAUD", "WIRE_FRAUD"])
        self.client.get(
            f"/api/synthetic/scenario/{typology}?n_transactions=5",
            name="GET /synthetic/scenario",
        )


class FeedbackTasks(SequentialTaskSet):
    """Simulates analyst RL feedback submission."""

    @task
    def get_feedback_metrics(self):
        self.client.get("/api/feedback/metrics", name="GET /feedback/metrics")


# ── User classes ─────────────────────────────────────────────────────────────

class ComplianceAnalyst(HttpUser):
    """
    Simulates a compliance analyst:
    • Mostly browses dashboard and alert queue
    • Occasionally triggers investigation
    """
    wait_time = between(2, 6)
    weight = 6  # 60% of users

    tasks = {
        AnalystDashboardTasks: 5,
        InvestigationPipelineTasks: 1,
        FeedbackTasks: 1,
    }


class AutomatedPipeline(HttpUser):
    """
    Simulates automated alert ingestion and investigation triggers.
    Heavier on investigation endpoints.
    """
    wait_time = between(1, 3)
    weight = 3  # 30% of users

    tasks = {
        InvestigationPipelineTasks: 3,
        AnalystDashboardTasks: 1,
    }


class DataEngineer(HttpUser):
    """
    Simulates a data engineer working with synthetic data and agent registry.
    """
    wait_time = between(3, 10)
    weight = 1  # 10% of users

    tasks = {
        SyntheticDataTasks: 3,
        FeedbackTasks: 1,
        AnalystDashboardTasks: 1,
    }
