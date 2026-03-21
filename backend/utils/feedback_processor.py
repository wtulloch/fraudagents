"""
Reinforcement Learning feedback processor.

Analysts mark agent outputs as correct or incorrect.
Feedback is accumulated in Cosmos DB and used to:
  1. Track per-agent accuracy metrics
  2. Generate fine-tuning datasets for model improvement
  3. Adjust agent weightings in the risk aggregator (online RL)
  4. Trigger CI/CD evaluation pipeline when enough feedback accumulates
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Minimum feedback samples before triggering fine-tune signal
FINE_TUNE_THRESHOLD = 100


class FeedbackProcessor:
    def __init__(self, cosmos_service) -> None:
        self.cosmos = cosmos_service

    async def submit(
        self,
        alert_id: str,
        agent_name: str,
        run_id: str,
        analyst_username: str,
        is_correct: bool,
        actual_risk_score: Optional[float] = None,
        actual_typology: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        feedback_id = str(uuid.uuid4())
        record = {
            "id": feedback_id,
            "alert_id": alert_id,
            "agent_name": agent_name,
            "run_id": run_id,
            "analyst": analyst_username,
            "is_correct": is_correct,
            "actual_risk_score": actual_risk_score,
            "actual_typology": actual_typology,
            "notes": notes or "",
            "used_for_training": False,
            "submitted_at": datetime.utcnow().isoformat(),
        }
        await self.cosmos.save_feedback(record)
        logger.info(
            "feedback_recorded",
            agent=agent_name,
            alert_id=alert_id,
            correct=is_correct,
        )
        return feedback_id

    async def get_agent_metrics(self, agent_name: str) -> Dict[str, Any]:
        """Calculate accuracy and precision metrics for an agent."""
        records = await self.cosmos.query(
            "feedback",
            "SELECT * FROM c WHERE c.agent_name = @agent",
            [{"name": "@agent", "value": agent_name}],
        )
        if not records:
            return {"agent_name": agent_name, "total": 0, "accuracy": None}

        total = len(records)
        correct = sum(1 for r in records if r.get("is_correct"))
        tp = sum(1 for r in records if r.get("is_correct") and r.get("actual_risk_score", 0) > 0.5)
        fp = sum(1 for r in records if not r.get("is_correct") and r.get("actual_risk_score", 0) <= 0.5)

        return {
            "agent_name": agent_name,
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total, 4),
            "true_positives": tp,
            "false_positives": fp,
            "precision": round(tp / (tp + fp), 4) if (tp + fp) > 0 else None,
            "fine_tune_ready": total >= FINE_TUNE_THRESHOLD,
        }

    async def get_all_agent_metrics(self) -> List[Dict[str, Any]]:
        agent_names = [
            "adverse-media-agent", "transaction-pattern-agent", "kyc-kyb-agent",
            "sanctions-matching-agent", "fraud-agent", "aml-agent",
        ]
        return [await self.get_agent_metrics(name) for name in agent_names]

    async def build_fine_tune_dataset(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Build a training dataset for fine-tuning from accumulated feedback.
        Returns OpenAI fine-tune format: [{messages: [{role, content}]}]
        """
        records = await self.cosmos.get_feedback_for_training(agent_name, limit=1000)
        dataset = []
        for record in records:
            if record.get("actual_typology") and record.get("actual_risk_score") is not None:
                dataset.append({
                    "messages": [
                        {"role": "system", "content": f"Agent: {agent_name}"},
                        {"role": "user", "content": f"Alert ID: {record['alert_id']}"},
                        {
                            "role": "assistant",
                            "content": f'{{"risk_score": {record["actual_risk_score"]}, "typology": "{record["actual_typology"]}"}}'
                        },
                    ]
                })
        logger.info(
            "fine_tune_dataset_built", agent=agent_name, samples=len(dataset)
        )
        return dataset
