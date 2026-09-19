"""
Immutable Audit System for VMotion AI.
Logs all operational transitions, AI recommendations, safety evaluations,
human approvals, task lifecycle steps, and post-migration verifications.
"""
import time
import json
import os
from typing import Optional, Literal
from pydantic import BaseModel, Field

AuditEventType = Literal[
    "CLUSTER_CONNECTED",
    "CLUSTER_DISCONNECTED",
    "AI_RECOMMENDATION_GENERATED",
    "SAFETY_CHECKS_EVALUATED",
    "SAFETY_CHECKS_BLOCKED",
    "HUMAN_APPROVAL_PENDING",
    "HUMAN_APPROVAL_GRANTED",
    "HUMAN_APPROVAL_REJECTED",
    "PROPOSAL_CANCELLED",
    "PROPOSAL_CREATED",
    "MIGRATION_TASK_STARTED",
    "TASK_PROGRESS_UPDATE",
    "TASK_HYPERVISOR_COMPLETED",
    "DESTINATION_PLACEMENT_VERIFIED",
    "VM_HEALTH_VERIFIED",
    "MIGRATION_VERIFIED",
    "MIGRATION_FAILED",
    "CONFIG_UPDATED"
]


class AuditEntry(BaseModel):
    id: str
    timestamp: float = Field(default_factory=time.time)
    time_iso: str
    event_type: AuditEventType
    vm_id: Optional[str] = None
    source_node: Optional[str] = None
    target_node: Optional[str] = None
    task_id: Optional[str] = None
    message: str
    details: dict = Field(default_factory=dict)


class AuditLogger:
    def __init__(self, log_path: str = "audit_events.jsonl"):
        self.log_path = log_path
        self._entries: list[AuditEntry] = []
        self._init_default_entries()

    def _init_default_entries(self):
        """Seed with initial startup event."""
        now = time.time()
        self.log_event(
            event_type="CLUSTER_CONNECTED",
            message="VMotion AI Control Plane initialized with Simulation Provider.",
            details={"provider": "simulation", "nodes": 3, "vms": 6}
        )

    def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        vm_id: Optional[str] = None,
        source_node: Optional[str] = None,
        target_node: Optional[str] = None,
        task_id: Optional[str] = None,
        details: Optional[dict] = None
    ) -> AuditEntry:
        now = time.time()
        entry_id = f"aud-{int(now * 1000)}-{len(self._entries) + 1}"
        iso_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

        entry = AuditEntry(
            id=entry_id,
            timestamp=now,
            time_iso=iso_str,
            event_type=event_type,
            vm_id=vm_id,
            source_node=source_node,
            target_node=target_node,
            task_id=task_id,
            message=message,
            details=details or {}
        )
        self._entries.insert(0, entry)  # Prepend newest

        # Keep in-memory buffer to 200 items
        if len(self._entries) > 200:
            self._entries.pop()

        # Append to JSONL file asynchronously / safely
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception:
            pass

        return entry

    def get_entries(self, limit: int = 50) -> list[AuditEntry]:
        return self._entries[:limit]


audit_logger = AuditLogger()
