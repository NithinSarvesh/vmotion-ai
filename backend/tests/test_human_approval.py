"""
Automated unit tests for Human Approval Workflow and Operator Governance.
"""
import pytest
from app.providers.simulation import SimulationProvider
from app.planner.planner import MigrationManager, ProposalState
from app.engine.base import Recommendation


@pytest.mark.asyncio
async def test_human_approval_workflow():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.collect_telemetry()

    rec = Recommendation(
        action_type="MIGRATE",
        vm_id="vm-101",
        vm_name="core-db-primary",
        source_node="node-01",
        target_node="node-02",
        reason="Test operator approval",
        engine_type="BASELINE_RULE",
        confidence_score=0.88,
        expected_load_balance_improvement=15.0,
        action_index=1,
        timestamp=100.0
    )

    # 1. Evaluate & propose: Must start in PENDING_APPROVAL
    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal is not None
    assert proposal.status == ProposalState.PENDING_APPROVAL
    assert proposal.approved_at is None
    assert proposal.rejected_at is None

    # 2. Operator Approval: Transition to TASK_RUNNING with task_id
    task_status = await manager.approve_proposal(proposal.proposal_id, "Authorized by Lead DevOps")
    assert proposal.status == ProposalState.TASK_RUNNING
    assert proposal.approved_at is not None
    assert proposal.task_id is not None
    assert task_status.task_id == proposal.task_id

    # 3. Double approval should raise ValueError
    with pytest.raises(ValueError) as exc:
        await manager.approve_proposal(proposal.proposal_id)
    assert "cannot approve" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_human_rejection_workflow():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.collect_telemetry()

    rec = Recommendation(
        action_type="MIGRATE",
        vm_id="vm-103",
        vm_name="api-gateway-edge",
        source_node="node-02",
        target_node="node-03",
        reason="Test operator rejection",
        engine_type="BASELINE_RULE",
        confidence_score=0.80,
        expected_load_balance_improvement=5.0,
        action_index=3,
        timestamp=100.0
    )

    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal.status == "PENDING_APPROVAL"

    # Operator Rejection
    rejected = await manager.reject_proposal(proposal.proposal_id, "Scheduled maintenance window conflict")
    assert rejected.status == "REJECTED"
    assert rejected.rejected_at is not None
    assert rejected.rejection_reason == "Scheduled maintenance window conflict"
    assert rejected.task_id is None


@pytest.mark.asyncio
async def test_blocked_proposal_cannot_be_approved():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.collect_telemetry()

    # Create recommendation targeting same node (forbidden by safety gate)
    rec = Recommendation(
        action_type="MIGRATE",
        vm_id="vm-101",
        vm_name="core-db-primary",
        source_node="node-01",
        target_node="node-01",  # Same node -> Blocked!
        reason="Invalid target test",
        engine_type="BASELINE_RULE",
        confidence_score=0.1,
        expected_load_balance_improvement=0.0,
        action_index=1,
        timestamp=100.0
    )

    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal.status == "BLOCKED"
    assert proposal.safety_evaluation.blocked is True

    # Attempting to approve must fail
    with pytest.raises(ValueError) as exc:
        await manager.approve_proposal(proposal.proposal_id)
    assert "cannot approve" in str(exc.value).lower()
