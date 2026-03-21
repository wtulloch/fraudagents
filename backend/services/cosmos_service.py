"""
Azure Cosmos DB service — session management, audit trail, HITL queue,
agent run history, feedback store, and case/alert persistence.

All containers use a consistent /partition_key structure for cost-optimised
cross-partition queries where needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions as cosmos_exceptions
from azure.identity.aio import ClientSecretCredential, DefaultAzureCredential

from backend.config import settings

logger = structlog.get_logger(__name__)

# ── Container definitions ─────────────────────────────────────────────────────
CONTAINERS: Dict[str, Dict[str, Any]] = {
    "alerts": {"partition_key": "/account_id", "ttl": None},
    "cases": {"partition_key": "/account_id", "ttl": None},
    "sessions": {"partition_key": "/session_id", "ttl": 86400},  # 24h TTL
    "agent_runs": {"partition_key": "/alert_id", "ttl": 2592000},  # 30-day TTL
    "audit_logs": {"partition_key": "/alert_id", "ttl": None},
    "hitl_queue": {"partition_key": "/alert_id", "ttl": None},
    "feedback": {"partition_key": "/alert_id", "ttl": None},
    "sar_documents": {"partition_key": "/case_id", "ttl": None},
    "synthetic_batches": {"partition_key": "/batch_id", "ttl": 604800},  # 7-day TTL
}


class CosmosService:
    def __init__(self) -> None:
        self._client: Optional[CosmosClient] = None
        self._db = None

    @property
    def client(self) -> CosmosClient:
        if self._client is None:
            if settings.azure_cosmos_key:
                credential = settings.azure_cosmos_key
            elif (
                settings.azure_tenant_id
                and settings.azure_client_id
                and settings.azure_client_secret
            ):
                credential = ClientSecretCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret,
                )
            else:
                credential = DefaultAzureCredential()
            self._client = CosmosClient(
                url=settings.azure_cosmos_endpoint,
                credential=credential,
            )
        return self._client

    async def _get_database(self):
        if self._db is None:
            self._db = self.client.get_database_client(settings.azure_cosmos_database)
        return self._db

    # ── Initialisation ────────────────────────────────────────────────────────

    async def ensure_containers(self) -> None:
        """Create database and containers if they do not exist."""
        db_client = self.client.get_database_client(settings.azure_cosmos_database)
        try:
            await self.client.create_database_if_not_exists(
                id=settings.azure_cosmos_database
            )
            logger.info("cosmos_db_ready", database=settings.azure_cosmos_database)
        except Exception as e:
            logger.warning("cosmos_db_ensure_warning", error=str(e))

        for container_name, config in CONTAINERS.items():
            try:
                kwargs: Dict[str, Any] = {
                    "id": container_name,
                    "partition_key": PartitionKey(path=config["partition_key"]),
                }
                if config.get("ttl"):
                    kwargs["default_ttl"] = config["ttl"]
                await db_client.create_container_if_not_exists(**kwargs)
                logger.debug("container_ready", container=container_name)
            except Exception as e:
                logger.warning("container_ensure_warning", container=container_name, error=str(e))

    # ── Generic CRUD ──────────────────────────────────────────────────────────

    async def upsert(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        db = await self._get_database()
        container = db.get_container_client(container_name)
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
        item["_updated_at"] = datetime.utcnow().isoformat()
        result = await container.upsert_item(item)
        return result

    async def get(
        self, container_name: str, item_id: str, partition_key: str
    ) -> Optional[Dict[str, Any]]:
        db = await self._get_database()
        container = db.get_container_client(container_name)
        try:
            return await container.read_item(item=item_id, partition_key=partition_key)
        except cosmos_exceptions.CosmosResourceNotFoundError:
            return None

    async def query(
        self, container_name: str, query: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        db = await self._get_database()
        container = db.get_container_client(container_name)
        items = container.query_items(
            query=query,
            parameters=parameters or [],
        )
        return [item async for item in items]

    # ── Alert ─────────────────────────────────────────────────────────────────

    async def save_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        return await self.upsert("alerts", alert)

    async def get_alert(self, alert_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        return await self.get("alerts", alert_id, account_id)

    async def list_alerts(
        self, status: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        if status:
            q = "SELECT * FROM c WHERE c.status = @status ORDER BY c.created_at DESC OFFSET @offset LIMIT @limit"
            params = [
                {"name": "@status", "value": status},
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ]
        else:
            q = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET @offset LIMIT @limit"
            params = [
                {"name": "@offset", "value": offset},
                {"name": "@limit", "value": limit},
            ]
        return await self.query("alerts", q, params)

    # ── Case ──────────────────────────────────────────────────────────────────

    async def save_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        return await self.upsert("cases", case)

    async def get_case(self, case_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        return await self.get("cases", case_id, account_id)

    # ── Agent Runs ────────────────────────────────────────────────────────────

    async def save_agent_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        return await self.upsert("agent_runs", run)

    async def get_agent_runs_for_alert(self, alert_id: str) -> List[Dict[str, Any]]:
        q = "SELECT * FROM c WHERE c.alert_id = @alert_id ORDER BY c._updated_at DESC"
        return await self.query("agent_runs", q, [{"name": "@alert_id", "value": alert_id}])

    # ── Session management ────────────────────────────────────────────────────

    async def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        result = await self.get("sessions", session_id, session_id)
        if result is None:
            result = {
                "id": session_id,
                "session_id": session_id,
                "messages": [],
                "context": {},
                "created_at": datetime.utcnow().isoformat(),
            }
            result = await self.upsert("sessions", result)
        return result

    async def append_session_message(
        self, session_id: str, role: str, content: str
    ) -> Dict[str, Any]:
        session = await self.get_or_create_session(session_id)
        session["messages"].append(
            {"role": role, "content": content, "ts": datetime.utcnow().isoformat()}
        )
        return await self.upsert("sessions", session)

    # ── HITL queue ────────────────────────────────────────────────────────────

    async def enqueue_hitl(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["queued_at"] = datetime.utcnow().isoformat()
        item["resolved"] = False
        return await self.upsert("hitl_queue", item)

    async def list_hitl_queue(self, resolved: bool = False) -> List[Dict[str, Any]]:
        q = "SELECT * FROM c WHERE c.resolved = @resolved ORDER BY c.queued_at ASC"
        return await self.query("hitl_queue", q, [{"name": "@resolved", "value": resolved}])

    async def resolve_hitl(
        self, item_id: str, alert_id: str, resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        item = await self.get("hitl_queue", item_id, alert_id)
        if item:
            item["resolved"] = True
            item["resolution"] = resolution
            item["resolved_at"] = datetime.utcnow().isoformat()
            return await self.upsert("hitl_queue", item)
        return {}

    # ── Feedback / RL ─────────────────────────────────────────────────────────

    async def save_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        feedback["submitted_at"] = datetime.utcnow().isoformat()
        return await self.upsert("feedback", feedback)

    async def get_feedback_for_training(
        self, agent_name: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        q = (
            "SELECT * FROM c WHERE c.agent_name = @agent_name "
            "AND c.used_for_training = false ORDER BY c.submitted_at ASC OFFSET 0 LIMIT @limit"
        )
        return await self.query(
            "feedback",
            q,
            [
                {"name": "@agent_name", "value": agent_name},
                {"name": "@limit", "value": limit},
            ],
        )

    # ── Audit log ─────────────────────────────────────────────────────────────

    async def log_audit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event["logged_at"] = datetime.utcnow().isoformat()
        return await self.upsert("audit_logs", event)

    # ── SAR ───────────────────────────────────────────────────────────────────

    async def save_sar(self, sar: Dict[str, Any]) -> Dict[str, Any]:
        return await self.upsert("sar_documents", sar)

    async def get_sar(self, sar_id: str, case_id: str) -> Optional[Dict[str, Any]]:
        return await self.get("sar_documents", sar_id, case_id)

    async def list_sars(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            q = "SELECT * FROM c WHERE c.status = @status ORDER BY c.drafted_at DESC"
            return await self.query("sar_documents", q, [{"name": "@status", "value": status}])
        return await self.query(
            "sar_documents", "SELECT * FROM c ORDER BY c.drafted_at DESC", []
        )

    # ── Dashboard metrics ─────────────────────────────────────────────────────

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        # GROUP BY + COUNT aggregates are unsupported by the Python SDK gateway path.
        # Fetch only the needed scalar fields and aggregate in Python instead.
        alert_rows = await self.query(
            "alerts", "SELECT c.status FROM c", []
        )
        alerts_by_status: Dict[str, int] = {}
        for row in alert_rows:
            s = row.get("status", "UNKNOWN")
            alerts_by_status[s] = alerts_by_status.get(s, 0) + 1

        sar_rows = await self.query(
            "sar_documents", "SELECT c.id FROM c", []
        )
        sars_total = len(sar_rows)

        hitl_rows = await self.query(
            "hitl_queue", "SELECT c.id FROM c WHERE c.resolved = false", []
        )
        hitl_pending = len(hitl_rows)

        return {
            "alerts_by_status": [
                {"status": k, "count": v} for k, v in alerts_by_status.items()
            ],
            "total_sars": sars_total,
            "hitl_pending": hitl_pending,
        }

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
