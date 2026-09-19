"""
Automated unit tests for VMotion AI Migration Lifecycle, Formal State Machine,
and Post-Migration Verification.
"""
import pytest
import asyncio
from app.providers.simulation import SimulationProvider
from app.planner.planner import (
    MigrationManager,
    ProposalState,
    InvalidStateTransitionError
)
from app.engine.rule_engine import RuleBasedDecisionEngine


@pytest.mark.asyncio
async def test_complete_migration_lifecycle_and_verification():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    engine = RuleBasedDecisionEngine()

    cluster = await provider.get_cluster_state()
    rec = engine.evaluate(cluster)
    assert rec.action_type == "MIGRATE", "Expected rule engine to recommend migration on unbalanced cluster"

    # Step 1: Proposal generation follows RECOMMENDED -> SAFETY_CHECK -> PENDING_APPROVAL
    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal is not None
    assert proposal.status == ProposalState.PENDING_APPROVAL
    assert proposal.safety_evaluation.passed is True

    # Check state history captured the progression
    history_states = [r.to_state for r in proposal.state_history]
    assert ProposalState.SAFETY_CHECK in history_states
    assert ProposalState.PENDING_APPROVAL in history_states

    # Step 2: Human Operator Approval follows PENDING_APPROVAL -> APPROVED -> DISPATCHED -> TASK_RUNNING
    task_status = await manager.approve_proposal(proposal.proposal_id, "Operator test authorization")
    assert proposal.status == ProposalState.TASK_RUNNING
    assert task_status.task_id is not None
    assert proposal.task_id == task_status.task_id

    # Step 3: Monitor until completion
    max_wait = 15.0
    start = asyncio.get_event_loop().time()
    while True:
        await asyncio.sleep(0.5)
        cur = await provider.monitor_task(task_status.task_id)
        if cur.state in ("VERIFIED", "FAILED"):
            break
        if asyncio.get_event_loop().time() - start > max_wait:
            pytest.fail("Migration did not complete within timeout")

    assert cur.state == "VERIFIED", f"Expected task to be VERIFIED, got {cur.state}"
    assert cur.progress_percent == 100.0

    # Wait for the background verification pipeline to settle
    await asyncio.sleep(0.5)
    assert proposal.status == ProposalState.VERIFIED

    # Verify final state history contains full progressive lifecycle
    final_states = [r.to_state for r in proposal.state_history]
    assert ProposalState.APPROVED in final_states
    assert ProposalState.DISPATCHED in final_states
    assert ProposalState.TASK_RUNNING in final_states
    assert ProposalState.VERIFYING in final_states
    assert ProposalState.VERIFIED in final_states

    # Step 4: Strict physical VM placement verification
    verified, msg = await provider.verify_migration(proposal.vm_id, proposal.target_node)
    assert verified is True, f"Placement verification failed: {msg}"


@pytest.mark.asyncio
async def test_illegal_state_transitions_raise_errors():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.get_cluster_state()
    engine = RuleBasedDecisionEngine()
    rec = engine.evaluate(cluster)
    
    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal.status == ProposalState.PENDING_APPROVAL

    # 1. Cannot transition directly from PENDING_APPROVAL to VERIFIED (skipping pipeline)
    with pytest.raises(InvalidStateTransitionError):
        proposal.transition_to(ProposalState.VERIFIED)

    # 2. Cannot transition directly to TASK_RUNNING without APPROVED and DISPATCHED
    with pytest.raises(InvalidStateTransitionError):
        proposal.transition_to(ProposalState.TASK_RUNNING)

    # 3. Reject proposal -> transitions to REJECTED (terminal state)
    await manager.reject_proposal(proposal.proposal_id, "Operator test rejection")
    assert proposal.status == ProposalState.REJECTED

    # 4. Cannot approve an already REJECTED proposal
    with pytest.raises(InvalidStateTransitionError):
        await manager.approve_proposal(proposal.proposal_id)

    # 5. Cannot transition from REJECTED to APPROVED
    with pytest.raises(InvalidStateTransitionError):
        proposal.transition_to(ProposalState.APPROVED)

    # 6. Cannot transition from REJECTED to CANCELLED (REJECTED is terminal)
    with pytest.raises(InvalidStateTransitionError):
        proposal.transition_to(ProposalState.CANCELLED)


@pytest.mark.asyncio
async def test_proposal_cancellation_workflow():
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.get_cluster_state()
    engine = RuleBasedDecisionEngine()
    rec = engine.evaluate(cluster)
    
    proposal = manager.evaluate_and_propose(rec, cluster)
    assert proposal.status == ProposalState.PENDING_APPROVAL

    # Operator cancels the proposal
    cancelled = await manager.cancel_proposal(proposal.proposal_id, "Maintenance cancelled by admin")
    assert cancelled.status == ProposalState.CANCELLED
    assert cancelled.cancellation_reason == "Maintenance cancelled by admin"
    assert cancelled.cancelled_at is not None

    # Cannot approve a cancelled proposal
    with pytest.raises(InvalidStateTransitionError):
        await manager.approve_proposal(proposal.proposal_id)
