"""
Automated unit tests for VMotion AI Deterministic Safety Gate.
"""
import pytest
import time
from app.providers.base import ClusterState, NodeTelemetry, VMTelemetry
from app.safety.gate import DeterministicSafetyGate


@pytest.fixture
def sample_cluster():
    return ClusterState(
        is_live=False,
        connected=True,
        provider_name="simulation",
        timestamp=time.time(),
        nodes={
            "node-01": NodeTelemetry(
                id="node-01",
                name="node-01.mgmt",
                status="online",
                cpu_cores=16,
                cpu_percent=82.0,
                ram_total_mb=65536.0,
                ram_used_mb=50000.0,
                ram_percent=76.3,
                shared_storage_accessible=True,
                quorum_healthy=True,
                active_vms=["vm-101"]
            ),
            "node-02": NodeTelemetry(
                id="node-02",
                name="node-02.mgmt",
                status="online",
                cpu_cores=16,
                cpu_percent=35.0,
                ram_total_mb=65536.0,
                ram_used_mb=20000.0,
                ram_percent=30.5,
                shared_storage_accessible=True,
                quorum_healthy=True,
                active_vms=[]
            ),
            "node-03": NodeTelemetry(
                id="node-03",
                name="node-03.mgmt",
                status="offline",
                cpu_cores=16,
                cpu_percent=0.0,
                ram_total_mb=65536.0,
                ram_used_mb=0.0,
                shared_storage_accessible=False,
                quorum_healthy=False,
                active_vms=[]
            )
        },
        vms={
            "vm-101": VMTelemetry(
                vmid="vm-101",
                name="test-workload",
                node_id="node-01",
                status="running",
                cpu_cores=4,
                cpu_percent=60.0,
                ram_allocated_mb=8192.0,
                ram_used_mb=6000.0,
                uptime_seconds=3600
            ),
            "vm-102": VMTelemetry(
                vmid="vm-102",
                name="stopped-workload",
                node_id="node-01",
                status="stopped",
                cpu_cores=2,
                cpu_percent=0.0,
                ram_allocated_mb=4096.0,
                ram_used_mb=0.0,
                uptime_seconds=0
            )
        }
    )


def test_safety_identical_source_and_destination(sample_cluster):
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-01")
    assert eval_result.blocked is True
    assert any("identical" in r.lower() for r in eval_result.rejection_reasons)


def test_safety_offline_destination(sample_cluster):
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-03")
    assert eval_result.blocked is True
    assert any("offline" in r.lower() for r in eval_result.rejection_reasons)


def test_safety_stopped_vm_blocked(sample_cluster):
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-102", "node-02")
    assert eval_result.blocked is True
    assert any("not running" in r.lower() for r in eval_result.rejection_reasons)


def test_safety_insufficient_ram(sample_cluster):
    gate = DeterministicSafetyGate()
    # Artificially exhaust node-02 memory
    sample_cluster.nodes["node-02"].ram_used_mb = 64000.0  # Only ~1536MB free, VM needs 8192MB
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    assert eval_result.blocked is True
    assert any("insufficient memory" in r.lower() for r in eval_result.rejection_reasons)


def test_safety_cooldown_enforcement(sample_cluster):
    gate = DeterministicSafetyGate(cooldown_seconds=60)
    sample_cluster.vms["vm-101"].last_migrated_at = time.time() - 20.0  # Migrated 20s ago
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    assert eval_result.blocked is True
    assert any("cooldown" in r.lower() for r in eval_result.rejection_reasons)


def test_safety_healthy_migration_passes(sample_cluster):
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    assert eval_result.blocked is False
    assert eval_result.passed is True
    assert eval_result.passed_checks == eval_result.total_checks


# ---------------------------------------------------------------------------
# AI CONTRADICTION & DECOUPLING TESTS (Requirement 8)
# Demonstrates that deterministic safety gate overrides any AI recommendation,
# regardless of engine confidence or claimed reward.
# ---------------------------------------------------------------------------

from app.engine.base import Recommendation
from app.planner.planner import MigrationManager, ProposalState
from app.providers.simulation import SimulationProvider
from app.audit.logger import audit_logger


def test_contradiction_ai_recommends_cpu_saturated_destination(sample_cluster):
    """AI recommends migrating to a saturated node (90% CPU) -> Deterministic safety strictly blocks."""
    # Saturate destination node-02
    sample_cluster.nodes["node-02"].cpu_percent = 84.0
    gate = DeterministicSafetyGate(max_cpu_percent=85.0)
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    
    assert eval_result.blocked is True
    assert eval_result.passed is False
    assert "ERR_CPU_OVERLOAD_PROJECTED" in eval_result.rejection_codes
    assert any("exceeding the 85.0% safety threshold" in r for r in eval_result.rejection_reasons)


def test_contradiction_ai_recommends_lost_quorum_destination(sample_cluster):
    """AI recommends migrating to a node with broken quorum -> Deterministic safety strictly blocks."""
    sample_cluster.nodes["node-02"].quorum_healthy = False
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    
    assert eval_result.blocked is True
    assert eval_result.passed is False
    assert "ERR_STORAGE_OR_QUORUM" in eval_result.rejection_codes


def test_contradiction_ai_recommends_inaccessible_storage(sample_cluster):
    """AI recommends migration when destination cannot access shared storage -> Strictly blocks."""
    sample_cluster.nodes["node-02"].shared_storage_accessible = False
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    
    assert eval_result.blocked is True
    assert eval_result.passed is False
    assert "ERR_STORAGE_OR_QUORUM" in eval_result.rejection_codes


def test_contradiction_ai_recommends_stopped_workload(sample_cluster):
    """AI recommends migrating a stopped VM -> Strictly blocks."""
    gate = DeterministicSafetyGate()
    eval_result = gate.evaluate(sample_cluster, "vm-102", "node-02")
    
    assert eval_result.blocked is True
    assert eval_result.passed is False
    assert "ERR_VM_NOT_RUNNING" in eval_result.rejection_codes


def test_contradiction_ai_recommends_during_cooldown(sample_cluster):
    """AI recommends migrating a VM that just moved 10s ago -> Cooldown blocks."""
    sample_cluster.vms["vm-101"].last_migrated_at = time.time() - 10.0
    gate = DeterministicSafetyGate(cooldown_seconds=60)
    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02")
    
    assert eval_result.blocked is True
    assert eval_result.passed is False
    assert "ERR_COOLDOWN_ACTIVE" in eval_result.rejection_codes


@pytest.mark.asyncio
async def test_safety_gate_blocks_ai_recommendation_and_logs_loudly():
    """
    End-to-end integration test:
    AI generates an objectively terrible recommendation (100% confidence, migrate to saturated node).
    MigrationManager processes it, safety gate fires, status is set to BLOCKED,
    and audit log loudly records SAFETY_CHECKS_BLOCKED.
    """
    provider = SimulationProvider()
    manager = MigrationManager(provider)
    cluster = await provider.get_cluster_state()

    # Artificially saturate node-02
    cluster.nodes["node-02"].cpu_percent = 92.0

    terrible_rec = Recommendation(
        action_type="MIGRATE",
        vm_id="vm-101",
        vm_name="core-db-primary",
        source_node="node-01",
        target_node="node-02",
        reason="Flawed RL policy attempts to cram workload into saturated node",
        engine_type="PPO_POLICY",
        confidence_score=1.0,  # 100% confidence!
        expected_load_balance_improvement=50.0,
        action_index=1,
        timestamp=time.time()
    )

    proposal = manager.evaluate_and_propose(terrible_rec, cluster)
    assert proposal is not None
    assert proposal.status == ProposalState.BLOCKED
    assert proposal.safety_evaluation.blocked is True
    assert proposal.safety_evaluation.passed is False

    # Verify audit trail contains SAFETY_CHECKS_BLOCKED event
    recent_logs = audit_logger.get_entries(limit=10)
    blocked_events = [e for e in recent_logs if e.event_type == "SAFETY_CHECKS_BLOCKED"]
    assert len(blocked_events) > 0
    latest_blocked = blocked_events[0]
    assert latest_blocked.vm_id == "vm-101"
    assert latest_blocked.target_node == "node-02"
    assert "BLOCKED" in latest_blocked.message


# ---------------------------------------------------------------------------
# STRATEGY-AWARE STORAGE SAFETY TESTS (Requirement 7 a-e)
# ---------------------------------------------------------------------------

def test_safety_shared_storage_migration_with_shared_datastore_allowed(sample_cluster):
    """
    Case 7.a: Shared-storage migration + shared datastore available.
    MUST be allowed by Rule 7.
    """
    gate = DeterministicSafetyGate()
    sample_cluster.nodes["node-02"].shared_storage_accessible = True
    sample_cluster.nodes["node-02"].storage_status = "HEALTHY"
    sample_cluster.nodes["node-02"].quorum_healthy = True

    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=False)
    storage_check = next(r for r in eval_result.results if r.check_name == "STORAGE_AND_QUORUM")

    assert storage_check.passed is True
    assert storage_check.code == "OK_STORAGE_AND_QUORUM"
    assert eval_result.passed is True
    assert "ERR_STORAGE_OR_QUORUM" not in eval_result.rejection_codes


def test_safety_shared_storage_migration_without_shared_datastore_blocked(sample_cluster):
    """
    Case 7.b: Shared-storage migration + datastore missing / not shared.
    MUST be strictly blocked by Rule 7.
    """
    gate = DeterministicSafetyGate()
    sample_cluster.nodes["node-02"].shared_storage_accessible = False
    sample_cluster.nodes["node-02"].storage_status = "HEALTHY"  # Local storage active, but no shared storage
    sample_cluster.nodes["node-02"].quorum_healthy = True

    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=False)
    storage_check = next(r for r in eval_result.results if r.check_name == "STORAGE_AND_QUORUM")

    assert storage_check.passed is False
    assert storage_check.code == "ERR_STORAGE_OR_QUORUM"
    assert eval_result.blocked is True
    assert "ERR_STORAGE_OR_QUORUM" in eval_result.rejection_codes


def test_safety_local_disk_migration_with_local_storage_allowed(sample_cluster):
    """
    Case 7.c: Local-disk migration + local target storage available + no shared storage.
    MUST NOT be blocked by the shared-storage requirement.
    """
    gate = DeterministicSafetyGate()
    sample_cluster.nodes["node-02"].shared_storage_accessible = False  # NO shared storage!
    sample_cluster.nodes["node-02"].storage_status = "HEALTHY"  # Active local storage ready for block mirror!
    sample_cluster.nodes["node-02"].quorum_healthy = True

    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=True)
    storage_check = next(r for r in eval_result.results if r.check_name == "STORAGE_AND_QUORUM")

    assert storage_check.passed is True
    assert storage_check.code == "OK_STORAGE_AND_QUORUM"
    assert eval_result.passed is True
    assert "ERR_STORAGE_OR_QUORUM" not in eval_result.rejection_codes


def test_safety_local_disk_migration_target_storage_unavailable_blocked(sample_cluster):
    """
    Case 7.d: Local-disk migration + destination storage unavailable/inactive.
    MUST be strictly blocked by Rule 7.
    """
    gate = DeterministicSafetyGate()
    sample_cluster.nodes["node-02"].shared_storage_accessible = False
    sample_cluster.nodes["node-02"].storage_status = "UNHEALTHY"  # Target storage offline / inactive!
    sample_cluster.nodes["node-02"].quorum_healthy = True

    eval_result = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=True)
    storage_check = next(r for r in eval_result.results if r.check_name == "STORAGE_AND_QUORUM")

    assert storage_check.passed is False
    assert storage_check.code == "ERR_STORAGE_OR_QUORUM"
    assert eval_result.blocked is True
    assert "ERR_STORAGE_OR_QUORUM" in eval_result.rejection_codes


def test_safety_unknown_storage_state_fails_closed(sample_cluster):
    """
    Case 7.e: Storage state is UNKNOWN (hypervisor storage API unreachable or returned error).
    MUST fail closed under both shared-storage and local-disk migration strategies.
    """
    gate = DeterministicSafetyGate()
    sample_cluster.nodes["node-02"].shared_storage_accessible = False
    sample_cluster.nodes["node-02"].storage_status = "UNKNOWN"
    sample_cluster.nodes["node-02"].quorum_healthy = True

    # Shared migration fails closed on UNKNOWN
    eval_shared = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=False)
    assert eval_shared.blocked is True
    assert "ERR_STORAGE_OR_QUORUM" in eval_shared.rejection_codes

    # Local-disk migration ALSO fails closed on UNKNOWN
    eval_local = gate.evaluate(sample_cluster, "vm-101", "node-02", with_local_disks=True)
    assert eval_local.blocked is True
    assert "ERR_STORAGE_OR_QUORUM" in eval_local.rejection_codes

    check_local = next(r for r in eval_local.results if r.check_name == "STORAGE_AND_QUORUM")
    assert "UNKNOWN" in check_local.explanation or "unverified" in check_local.explanation.lower()
