"""
Migration Planner & Lifecycle Orchestrator for VMotion AI.
Coordinates AI recommendations, deterministic safety checks, human approval,
hypervisor execution, continuous task monitoring, and post-migration placement verification.
"""
import time
import uuid
import asyncio
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field

from app.providers.base import (
    BaseVirtualizationProvider,
    ClusterState,
    MigrationPlan,
    MigrationTaskStatus,
    MigrationState
)
from app.engine.base import Recommendation
from app.safety.gate import deterministic_safety_gate, SafetyEvaluation, DeterministicSafetyGate
from app.audit.logger import audit_logger
from app.config import settings


class ProposalState(str, Enum):
    # Progressive lifecycle
    RECOMMENDED = "RECOMMENDED"
    SAFETY_CHECK = "SAFETY_CHECK"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    TASK_RUNNING = "TASK_RUNNING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"

    # Terminal / Failure states
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InvalidStateTransitionError(ValueError):
    def __init__(self, current_state: ProposalState | str, target_state: ProposalState | str, reason: str = ""):
        message = f"Invalid state transition from '{current_state}' to '{target_state}'."
        if reason:
            message += f" Reason: {reason}"
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


VALID_STATE_TRANSITIONS: dict[ProposalState, set[ProposalState]] = {
    ProposalState.RECOMMENDED: {
        ProposalState.SAFETY_CHECK,
        ProposalState.CANCELLED,
    },
    ProposalState.SAFETY_CHECK: {
        ProposalState.PENDING_APPROVAL,
        ProposalState.BLOCKED,
        ProposalState.CANCELLED,
    },
    ProposalState.PENDING_APPROVAL: {
        ProposalState.APPROVED,
        ProposalState.REJECTED,
        ProposalState.CANCELLED,
    },
    ProposalState.APPROVED: {
        ProposalState.DISPATCHED,
        ProposalState.CANCELLED,
    },
    ProposalState.DISPATCHED: {
        ProposalState.TASK_RUNNING,
        ProposalState.FAILED,
        ProposalState.CANCELLED,
    },
    ProposalState.TASK_RUNNING: {
        ProposalState.VERIFYING,
        ProposalState.FAILED,
        ProposalState.CANCELLED,
    },
    ProposalState.VERIFYING: {
        ProposalState.VERIFIED,
        ProposalState.FAILED,
    },
    # Terminal states: no further transitions permitted
    ProposalState.VERIFIED: set(),
    ProposalState.REJECTED: set(),
    ProposalState.BLOCKED: set(),
    ProposalState.FAILED: set(),
    ProposalState.CANCELLED: set(),
}


class StateTransitionRecord(BaseModel):
    from_state: ProposalState
    to_state: ProposalState
    timestamp: float = Field(default_factory=time.time)
    reason: Optional[str] = None


class PendingProposal(BaseModel):
    proposal_id: str
    vm_id: str
    vm_name: str
    source_node: str
    target_node: str
    reason: str
    engine_type: str
    confidence_score: float
    safety_evaluation: SafetyEvaluation
    status: ProposalState = ProposalState.RECOMMENDED
    created_at: float = Field(default_factory=time.time)
    approved_at: Optional[float] = None
    rejected_at: Optional[float] = None
    rejection_reason: Optional[str] = None
    cancelled_at: Optional[float] = None
    cancellation_reason: Optional[str] = None
    task_id: Optional[str] = None
    state_history: list[StateTransitionRecord] = Field(default_factory=list)

    def transition_to(self, target: ProposalState, reason: Optional[str] = None):
        allowed = VALID_STATE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidStateTransitionError(self.status, target, reason or "Transition not allowed by state machine")
        prev = self.status
        self.status = target
        self.state_history.append(
            StateTransitionRecord(
                from_state=prev,
                to_state=target,
                timestamp=time.time(),
                reason=reason
            )
        )


class MigrationManager:
    def __init__(self, provider: BaseVirtualizationProvider, safety_gate: Optional[DeterministicSafetyGate] = None):
        self.provider = provider
        self.safety_gate = safety_gate or deterministic_safety_gate
        self.proposals: dict[str, PendingProposal] = {}
        self.active_tasks: dict[str, MigrationTaskStatus] = {}
        self.completed_tasks: list[MigrationTaskStatus] = []

    def evaluate_and_propose(self, rec: Recommendation, cluster: ClusterState) -> Optional[PendingProposal]:
        if rec.action_type != "MIGRATE" or not rec.vm_id or not rec.target_node:
            return None

        # Check if an identical proposal is already pending or actively executing
        active_states = {
            ProposalState.RECOMMENDED,
            ProposalState.SAFETY_CHECK,
            ProposalState.PENDING_APPROVAL,
            ProposalState.APPROVED,
            ProposalState.DISPATCHED,
            ProposalState.TASK_RUNNING,
            ProposalState.VERIFYING,
        }
        for existing in self.proposals.values():
            if existing.vm_id == rec.vm_id and existing.status in active_states:
                return existing

        proposal_id = f"prop-{uuid.uuid4().hex[:8]}"
        
        # Step 1: Initialize in RECOMMENDED state
        proposal = PendingProposal(
            proposal_id=proposal_id,
            vm_id=rec.vm_id,
            vm_name=rec.vm_name or rec.vm_id,
            source_node=rec.source_node or "unknown",
            target_node=rec.target_node,
            reason=rec.reason,
            engine_type=rec.engine_type,
            confidence_score=rec.confidence_score,
            safety_evaluation=SafetyEvaluation(
                vm_id=rec.vm_id,
                source_node=rec.source_node or "unknown",
                target_node=rec.target_node,
                passed=False,
                blocked=False,
                total_checks=8,
                passed_checks=0
            ),
            status=ProposalState.RECOMMENDED
        )
        self.proposals[proposal_id] = proposal

        audit_logger.log_event(
            event_type="AI_RECOMMENDATION_GENERATED",
            vm_id=rec.vm_id,
            source_node=rec.source_node,
            target_node=rec.target_node,
            message=f"AI ({rec.engine_type}) proposed migration of {rec.vm_id} -> {rec.target_node} ({rec.reason}).",
            details={
                "proposal_id": proposal_id,
                "engine_type": rec.engine_type,
                "confidence": rec.confidence_score,
                "metrics": rec.metrics_summary
            }
        )

        # Step 2: Transition to SAFETY_CHECK
        proposal.transition_to(ProposalState.SAFETY_CHECK, "Commencing deterministic safety gate evaluation")

        # Run Deterministic Safety Gate
        safety_eval = self.safety_gate.evaluate(cluster, rec.vm_id, rec.target_node)
        proposal.safety_evaluation = safety_eval

        audit_logger.log_event(
            event_type="SAFETY_CHECKS_EVALUATED" if safety_eval.passed else "SAFETY_CHECKS_BLOCKED",
            vm_id=rec.vm_id,
            source_node=rec.source_node,
            target_node=rec.target_node,
            message=f"Safety Gate: {safety_eval.passed_checks}/{safety_eval.total_checks} checks passed." + 
                    (f" BLOCKED: {', '.join(safety_eval.rejection_reasons)}" if safety_eval.blocked else " All criteria satisfied."),
            details={"proposal_id": proposal_id, "passed": safety_eval.passed, "blocked": safety_eval.blocked, "reasons": safety_eval.rejection_reasons}
        )

        # Step 3: Transition to BLOCKED or PENDING_APPROVAL
        if safety_eval.blocked:
            proposal.transition_to(ProposalState.BLOCKED, f"Safety checks failed: {', '.join(safety_eval.rejection_reasons)}")
        else:
            proposal.transition_to(ProposalState.PENDING_APPROVAL, "All safety checks satisfied; awaiting operator approval")
            audit_logger.log_event(
                event_type="HUMAN_APPROVAL_PENDING",
                vm_id=rec.vm_id,
                source_node=rec.source_node,
                target_node=rec.target_node,
                message=f"Migration proposal {proposal_id} awaiting manual operator authorization.",
                details={"proposal_id": proposal_id}
            )

        return proposal

    async def approve_proposal(self, proposal_id: str, operator_notes: str = "Approved by operator") -> MigrationTaskStatus:
        if proposal_id not in self.proposals:
            raise KeyError(f"Proposal '{proposal_id}' not found.")
        
        proposal = self.proposals[proposal_id]
        if proposal.status != ProposalState.PENDING_APPROVAL:
            raise InvalidStateTransitionError(
                proposal.status,
                ProposalState.APPROVED,
                f"Proposal is in state '{proposal.status}', cannot approve."
            )
        
        if proposal.safety_evaluation.blocked:
            raise ValueError(f"Cannot approve blocked proposal: {proposal.safety_evaluation.rejection_reasons}")

        # State transition: PENDING_APPROVAL -> APPROVED
        proposal.transition_to(ProposalState.APPROVED, operator_notes)
        proposal.approved_at = time.time()

        audit_logger.log_event(
            event_type="HUMAN_APPROVAL_GRANTED",
            vm_id=proposal.vm_id,
            source_node=proposal.source_node,
            target_node=proposal.target_node,
            message=f"Operator authorization received for {proposal.vm_id} migration -> {proposal.target_node}.",
            details={"operator_notes": operator_notes, "proposal_id": proposal_id}
        )

        # Acquire safety lock to prevent concurrent migrations of same workload
        self.safety_gate.acquire_lock(proposal.vm_id)

        # Create execution plan
        plan = MigrationPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            vm_id=proposal.vm_id,
            source_node=proposal.source_node,
            target_node=proposal.target_node,
            reason=proposal.reason,
            created_at=time.time(),
            recommended_by="AI_PPO" if "PPO" in proposal.engine_type else "BASELINE_RULE"
        )

        # State transition: APPROVED -> DISPATCHED
        proposal.transition_to(ProposalState.DISPATCHED, "Dispatching migration plan to hypervisor provider")

        try:
            task_id = await self.provider.execute_migration(plan)
            proposal.task_id = task_id
            # State transition: DISPATCHED -> TASK_RUNNING
            proposal.transition_to(ProposalState.TASK_RUNNING, f"Hypervisor task running with ID: {task_id}")

            audit_logger.log_event(
                event_type="MIGRATION_TASK_STARTED",
                vm_id=proposal.vm_id,
                source_node=proposal.source_node,
                target_node=proposal.target_node,
                task_id=task_id,
                message=f"Live migration job dispatched to hypervisor. Task ID: {task_id}.",
                details={"task_id": task_id, "plan_id": plan.plan_id}
            )

            initial_status = await self.provider.monitor_task(task_id)
            self.active_tasks[task_id] = initial_status

            # Spawn background monitoring and verification loop
            asyncio.create_task(self._monitor_and_verify_pipeline(task_id, proposal))
            return initial_status

        except Exception as exc:
            proposal.transition_to(ProposalState.FAILED, f"Hypervisor dispatch failed: {str(exc)}")
            self.safety_gate.release_lock(proposal.vm_id)
            raise

    async def reject_proposal(self, proposal_id: str, reason: str = "Operator declined") -> PendingProposal:
        if proposal_id not in self.proposals:
            raise KeyError(f"Proposal '{proposal_id}' not found.")
        
        proposal = self.proposals[proposal_id]
        if proposal.status != ProposalState.PENDING_APPROVAL:
            raise InvalidStateTransitionError(
                proposal.status,
                ProposalState.REJECTED,
                f"Proposal is in state '{proposal.status}', cannot reject."
            )

        proposal.transition_to(ProposalState.REJECTED, reason)
        proposal.rejected_at = time.time()
        proposal.rejection_reason = reason

        audit_logger.log_event(
            event_type="HUMAN_APPROVAL_REJECTED",
            vm_id=proposal.vm_id,
            source_node=proposal.source_node,
            target_node=proposal.target_node,
            message=f"Operator rejected migration proposal: {reason}.",
            details={"reason": reason, "proposal_id": proposal_id}
        )
        return proposal

    async def cancel_proposal(self, proposal_id: str, reason: str = "Operator cancelled") -> PendingProposal:
        if proposal_id not in self.proposals:
            raise KeyError(f"Proposal '{proposal_id}' not found.")
        
        proposal = self.proposals[proposal_id]
        proposal.transition_to(ProposalState.CANCELLED, reason)
        proposal.cancelled_at = time.time()
        proposal.cancellation_reason = reason
        self.safety_gate.release_lock(proposal.vm_id)

        audit_logger.log_event(
            event_type="PROPOSAL_CANCELLED",
            vm_id=proposal.vm_id,
            source_node=proposal.source_node,
            target_node=proposal.target_node,
            message=f"Migration proposal {proposal_id} was cancelled: {reason}.",
            details={"proposal_id": proposal_id, "reason": reason}
        )
        return proposal

    async def _monitor_and_verify_pipeline(self, task_id: str, proposal: PendingProposal):
        """Monitors task execution, verifies actual placement and health, records audit trail."""
        try:
            while True:
                await asyncio.sleep(1.0)
                status = await self.provider.monitor_task(task_id)
                self.active_tasks[task_id] = status

                if status.state in ("VERIFIED", "FAILED", "BLOCKED"):
                    break

            if status.state == "VERIFIED":
                # State transition: TASK_RUNNING -> VERIFYING
                proposal.transition_to(ProposalState.VERIFYING, "Querying hypervisor for placement and workload health")
                
                # Strict verification phase: query actual placement and workload health
                p_ok, p_msg = await self.provider.verify_placement(proposal.vm_id, proposal.target_node)
                h_ok, h_msg = await self.provider.verify_vm_health(proposal.vm_id)
                
                if p_ok and h_ok:
                    # State transition: VERIFYING -> VERIFIED
                    proposal.transition_to(ProposalState.VERIFIED, "Placement and health checks confirmed")
                    
                    audit_logger.log_event(
                        event_type="DESTINATION_PLACEMENT_VERIFIED",
                        vm_id=proposal.vm_id,
                        target_node=proposal.target_node,
                        task_id=task_id,
                        message=f"Post-migration query confirmed: Workload '{proposal.vm_id}' is placed on '{proposal.target_node}'.",
                        details=status.verification_details or {}
                    )
                    audit_logger.log_event(
                        event_type="VM_HEALTH_VERIFIED",
                        vm_id=proposal.vm_id,
                        target_node=proposal.target_node,
                        task_id=task_id,
                        message=f"Workload '{proposal.vm_id}' operational health check confirmed (status: running).",
                        details={"status": "running"}
                    )
                    provider_tag = "Simulation" if "sim" in str(self.provider.__class__.__name__).lower() else "Live Hypervisor"
                    audit_logger.log_event(
                        event_type="MIGRATION_VERIFIED",
                        vm_id=proposal.vm_id,
                        source_node=proposal.source_node,
                        target_node=proposal.target_node,
                        task_id=task_id,
                        message=f"{provider_tag} migration lifecycle completed and verified.",
                        details=status.verification_details or {}
                    )
                else:
                    err_msg = p_msg if not p_ok else h_msg
                    status.state = "FAILED"
                    status.error = f"Verification failed: {err_msg}"
                    proposal.transition_to(ProposalState.FAILED, f"Verification failed: {err_msg}")
                    audit_logger.log_event(
                        event_type="MIGRATION_FAILED",
                        vm_id=proposal.vm_id,
                        task_id=task_id,
                        message=f"Verification failure: {err_msg}",
                        details={"error": err_msg}
                    )

            elif status.state == "FAILED":
                proposal.transition_to(ProposalState.FAILED, f"Hypervisor task failed: {status.error}")
                audit_logger.log_event(
                    event_type="MIGRATION_FAILED",
                    vm_id=proposal.vm_id,
                    task_id=task_id,
                    message=f"Hypervisor task failed: {status.error}",
                    details={"error": status.error}
                )

        finally:
            # Release lock & archive task
            self.safety_gate.release_lock(proposal.vm_id)
            if task_id in self.active_tasks:
                task_status = self.active_tasks.pop(task_id)
                self.completed_tasks.insert(0, task_status)
                if len(self.completed_tasks) > 50:
                    self.completed_tasks.pop()
