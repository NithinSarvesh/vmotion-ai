"""
Base Decision Engine Interface for VMotion AI.
Defines contracts for recommendation generation and action masking.
"""
from abc import ABC, abstractmethod
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.providers.base import ClusterState


class Recommendation(BaseModel):
    action_type: Literal["MIGRATE", "NO_OP"] = "NO_OP"
    vm_id: Optional[str] = None
    vm_name: Optional[str] = None
    source_node: Optional[str] = None
    target_node: Optional[str] = None
    reason: str = "Cluster load is balanced. No migration recommended."
    engine_type: Literal["PPO_POLICY", "BASELINE_RULE", "NO_OP"] = "NO_OP"
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    expected_load_balance_improvement: float = 0.0
    action_index: int = 0  # 0 = No-op, 1..N = VM index
    timestamp: float = 0.0
    metrics_summary: dict = Field(default_factory=dict)


class BaseDecisionEngine(ABC):
    @abstractmethod
    def evaluate(self, cluster: ClusterState) -> Recommendation:
        """Evaluate cluster telemetry and return an actionable recommendation."""
        pass
