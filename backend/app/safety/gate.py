"""
Deterministic Safety Gate for VMotion AI.
Guarantees that no AI recommendation or manual operator command can compromise cluster stability.
Every candidate migration must pass all 8 mandatory deterministic safety rules.

Every check explicitly returns:
- passed: bool
- code: str (machine-readable reason code)
- explanation: str (human-readable explanation)
- message: str
- metric_value: Optional[str]
"""
import time
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.providers.base import ClusterState
from app.config import settings


class SafetyCheckResult(BaseModel):
    check_name: str
    passed: bool
    code: str  # Machine-readable reason code
    explanation: str  # Human-readable explanation
    severity: Literal["CRITICAL", "WARNING"] = "CRITICAL"
    message: str
    metric_value: Optional[str] = None


class SafetyEvaluation(BaseModel):
    vm_id: str
    source_node: str
    target_node: str
    passed: bool
    blocked: bool
    total_checks: int
    passed_checks: int
    evaluated_at: float = Field(default_factory=time.time)
    results: list[SafetyCheckResult] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    rejection_codes: list[str] = Field(default_factory=list)


class DeterministicSafetyGate:
    def __init__(self, cooldown_seconds: int = 60, max_cpu_percent: float = 85.0, max_ram_percent: float = 90.0):
        self.cooldown_seconds = cooldown_seconds
        self.max_cpu_percent = max_cpu_percent
        self.max_ram_percent = max_ram_percent
        self._active_migration_locks: set[str] = set()

    def acquire_lock(self, vm_id: str):
        self._active_migration_locks.add(vm_id)

    def release_lock(self, vm_id: str):
        self._active_migration_locks.discard(vm_id)

    def evaluate(self, cluster: ClusterState, vm_id: str, target_node_id: str) -> SafetyEvaluation:
        now = time.time()
        results: list[SafetyCheckResult] = []
        rejection_reasons: list[str] = []
        rejection_codes: list[str] = []

        vm = cluster.vms.get(vm_id)
        target_node = cluster.nodes.get(target_node_id)
        source_node = cluster.nodes.get(vm.node_id) if vm else None

        # Rule 1: VM Exists & Operational State
        if not vm:
            code = "ERR_VM_NOT_FOUND"
            msg = f"VM '{vm_id}' does not exist in cluster inventory."
            expl = "The requested workload identifier was not found in the hypervisor cluster registry."
            results.append(SafetyCheckResult(
                check_name="VM_EXISTENCE",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append(expl)
            rejection_codes.append(code)
        elif vm.status != "running":
            code = "ERR_VM_NOT_RUNNING"
            msg = f"VM '{vm_id}' is in '{vm.status}' state."
            expl = f"Live migration requires an active running workload; current hypervisor status is '{vm.status}'."
            results.append(SafetyCheckResult(
                check_name="VM_RUNNING_STATE",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append(f"Workload is not running (status: {vm.status}).")
            rejection_codes.append(code)
        else:
            results.append(SafetyCheckResult(
                check_name="VM_RUNNING_STATE",
                passed=True,
                code="OK_VM_RUNNING",
                explanation=f"Workload '{vm_id}' is active and operational (uptime: {vm.uptime_seconds // 3600}h).",
                message=f"VM '{vm_id}' operational state confirmed."
            ))

        # Rule 2: Distinct Source and Destination
        if vm and vm.node_id == target_node_id:
            code = "ERR_IDENTICAL_SOURCE_DEST"
            msg = f"Source and destination compute nodes are identical ('{target_node_id}')."
            expl = f"Source node and destination node are identical ('{target_node_id}')."
            results.append(SafetyCheckResult(
                check_name="DISTINCT_TARGET",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append("Source and destination nodes are identical.")
            rejection_codes.append(code)
        else:
            results.append(SafetyCheckResult(
                check_name="DISTINCT_TARGET",
                passed=True,
                code="OK_DISTINCT_TARGET",
                explanation=f"Inter-node rebalance trajectory validated: {vm.node_id if vm else 'unknown'} -> {target_node_id}.",
                message="Target compute node is distinct from source node."
            ))

        # Rule 3: Source Node Health
        if not source_node or source_node.status != "online":
            code = "ERR_SOURCE_NODE_OFFLINE"
            status_desc = source_node.status if source_node else "unreachable"
            msg = f"Source compute node is {status_desc}."
            expl = f"Source node is offline or degraded ({status_desc})."
            results.append(SafetyCheckResult(
                check_name="SOURCE_NODE_HEALTH",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append(expl)
            rejection_codes.append(code)
        else:
            results.append(SafetyCheckResult(
                check_name="SOURCE_NODE_HEALTH",
                passed=True,
                code="OK_SOURCE_HEALTHY",
                explanation=f"Source node '{source_node.name}' daemon is healthy with active heartbeat.",
                message="Source compute node is online and healthy."
            ))

        # Rule 4: Destination Node Health
        if not target_node or target_node.status != "online":
            code = "ERR_DEST_NODE_OFFLINE"
            status_desc = target_node.status if target_node else "unreachable"
            msg = f"Destination compute node '{target_node_id}' is {status_desc}."
            expl = f"Destination node is offline or unreachable ({status_desc})."
            results.append(SafetyCheckResult(
                check_name="DEST_NODE_HEALTH",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append(expl)
            rejection_codes.append(code)
        else:
            results.append(SafetyCheckResult(
                check_name="DEST_NODE_HEALTH",
                passed=True,
                code="OK_DEST_HEALTHY",
                explanation=f"Destination node '{target_node.name}' daemon is online and responsive over cluster network.",
                message="Destination compute node is online and reachable."
            ))

        # Rule 5: Destination RAM Capacity
        if vm and target_node:
            free_ram_mb = target_node.ram_total_mb - target_node.ram_used_mb
            if free_ram_mb < vm.ram_allocated_mb:
                code = "ERR_INSUFFICIENT_RAM"
                msg = f"Insufficient RAM on '{target_node_id}'. Free: {free_ram_mb:.0f}MB, Required: {vm.ram_allocated_mb:.0f}MB."
                expl = f"Destination node has insufficient memory (Free: {free_ram_mb:.0f}MB, Required: {vm.ram_allocated_mb:.0f}MB)."
                results.append(SafetyCheckResult(
                    check_name="DEST_RAM_HEADROOM",
                    passed=False,
                    code=code,
                    explanation=expl,
                    severity="CRITICAL",
                    message=msg,
                    metric_value=f"{free_ram_mb:.0f}MB free < {vm.ram_allocated_mb:.0f}MB req"
                ))
                rejection_reasons.append("Destination node has insufficient memory.")
                rejection_codes.append(code)
            else:
                results.append(SafetyCheckResult(
                    check_name="DEST_RAM_HEADROOM",
                    passed=True,
                    code="OK_RAM_HEADROOM",
                    explanation=f"Destination node memory verified. Headroom post-migration: {(free_ram_mb - vm.ram_allocated_mb):.0f}MB unallocated.",
                    message="Destination node memory capacity verified.",
                    metric_value=f"{(free_ram_mb - vm.ram_allocated_mb):.0f}MB free post-mig"
                ))
        else:
            code = "ERR_RAM_TELEMETRY_MISSING"
            results.append(SafetyCheckResult(
                check_name="DEST_RAM_HEADROOM",
                passed=False,
                code=code,
                explanation="Cannot verify destination RAM headroom due to missing telemetry data.",
                severity="CRITICAL",
                message="Missing telemetry for RAM headroom calculation."
            ))
            rejection_reasons.append("Missing telemetry for RAM headroom.")
            rejection_codes.append(code)

        # Rule 6: Destination CPU Capacity & Overload Prevention
        if vm and target_node:
            projected_additional_load = (vm.cpu_cores / target_node.cpu_cores) * (vm.cpu_percent * 0.8)
            projected_total_cpu = target_node.cpu_percent + projected_additional_load
            if projected_total_cpu > self.max_cpu_percent:
                code = "ERR_CPU_OVERLOAD_PROJECTED"
                msg = f"Projected destination CPU ({projected_total_cpu:.1f}%) exceeds safety ceiling ({self.max_cpu_percent:.1f}%)."
                expl = f"Adding workload '{vm_id}' to '{target_node_id}' would push CPU to {projected_total_cpu:.1f}%, exceeding the {self.max_cpu_percent:.1f}% safety threshold."
                results.append(SafetyCheckResult(
                    check_name="DEST_CPU_CAPACITY",
                    passed=False,
                    code=code,
                    explanation=expl,
                    severity="CRITICAL",
                    message=msg,
                    metric_value=f"Projected {projected_total_cpu:.1f}% > {self.max_cpu_percent:.1f}%"
                ))
                rejection_reasons.append(expl)
                rejection_codes.append(code)
            else:
                results.append(SafetyCheckResult(
                    check_name="DEST_CPU_CAPACITY",
                    passed=True,
                    code="OK_CPU_HEADROOM",
                    explanation=f"Destination compute capacity verified. Projected post-migration CPU load is {projected_total_cpu:.1f}%.",
                    message="Destination CPU headroom verified.",
                    metric_value=f"Projected {projected_total_cpu:.1f}% <= {self.max_cpu_percent:.1f}%"
                ))

        # Rule 7: Storage & Cluster Quorum Health
        if target_node:
            storage_ok = target_node.shared_storage_accessible
            quorum_ok = target_node.quorum_healthy
            if not storage_ok or not quorum_ok:
                code = "ERR_STORAGE_OR_QUORUM"
                msg = f"Cluster quorum or shared storage degraded (Storage: {storage_ok}, Quorum: {quorum_ok})."
                expl = "Live migration requires shared storage access and cluster quorum consensus."
                results.append(SafetyCheckResult(
                    check_name="STORAGE_AND_QUORUM",
                    passed=False,
                    code=code,
                    explanation=expl,
                    severity="CRITICAL",
                    message=msg
                ))
                rejection_reasons.append(expl)
                rejection_codes.append(code)
            else:
                results.append(SafetyCheckResult(
                    check_name="STORAGE_AND_QUORUM",
                    passed=True,
                    code="OK_STORAGE_AND_QUORUM",
                    explanation="Shared datastore accessibility confirmed and cluster quorum consensus verified.",
                    message="Storage and quorum health verified."
                ))

        # Rule 8: Conflict Lock & Migration Cooldown
        if vm_id in self._active_migration_locks or (vm and vm.status == "migrating"):
            code = "ERR_MIGRATION_CONFLICT_LOCK"
            msg = f"Workload '{vm_id}' is already involved in an active migration task."
            expl = f"Lock conflict: A live migration task is already in progress for '{vm_id}'. Concurrent migrations are forbidden."
            results.append(SafetyCheckResult(
                check_name="MIGRATION_CONFLICT",
                passed=False,
                code=code,
                explanation=expl,
                severity="CRITICAL",
                message=msg
            ))
            rejection_reasons.append(expl)
            rejection_codes.append(code)
        elif vm and vm.last_migrated_at:
            elapsed = now - vm.last_migrated_at
            if elapsed < self.cooldown_seconds:
                remaining = int(self.cooldown_seconds - elapsed)
                code = "ERR_COOLDOWN_ACTIVE"
                msg = f"Migration cooldown active for '{vm_id}'. Remaining: {remaining}s."
                expl = f"Workload '{vm_id}' was migrated {int(elapsed)}s ago. Must wait {remaining}s to satisfy the {self.cooldown_seconds}s cooldown policy."
                results.append(SafetyCheckResult(
                    check_name="COOLDOWN_PERIOD",
                    passed=False,
                    code=code,
                    explanation=expl,
                    severity="CRITICAL",
                    message=msg,
                    metric_value=f"{remaining}s remaining"
                ))
                rejection_reasons.append(expl)
                rejection_codes.append(code)
            else:
                results.append(SafetyCheckResult(
                    check_name="COOLDOWN_PERIOD",
                    passed=True,
                    code="OK_COOLDOWN_SATISFIED",
                    explanation=f"Cooldown satisfied (last migration was {int(elapsed)}s ago, exceeding {self.cooldown_seconds}s threshold).",
                    message="Cooldown period satisfied."
                ))
        else:
            results.append(SafetyCheckResult(
                check_name="COOLDOWN_PERIOD",
                passed=True,
                code="OK_COOLDOWN_SATISFIED",
                explanation="No prior migration record for this workload; cooldown satisfied.",
                message="Cooldown period satisfied."
            ))

        passed_count = sum(1 for r in results if r.passed)
        is_blocked = len(rejection_reasons) > 0

        return SafetyEvaluation(
            vm_id=vm_id,
            source_node=vm.node_id if vm else "unknown",
            target_node=target_node_id,
            passed=not is_blocked,
            blocked=is_blocked,
            total_checks=len(results),
            passed_checks=passed_count,
            results=results,
            rejection_reasons=rejection_reasons,
            rejection_codes=rejection_codes
        )


safety_gate = DeterministicSafetyGate(
    cooldown_seconds=settings.SAFETY_COOLDOWN_SECONDS,
    max_cpu_percent=settings.SAFETY_MAX_CPU_PERCENT,
    max_ram_percent=settings.SAFETY_MAX_RAM_PERCENT
)
deterministic_safety_gate = safety_gate
