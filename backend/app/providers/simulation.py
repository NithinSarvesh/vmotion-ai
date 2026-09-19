"""
High-Fidelity Simulation Virtualization Provider for VMotion AI.
Accurately models multi-node cluster physics, live telemetry drift,
asynchronous multi-stage migration execution, and strict verification states.
All data is explicitly marked with provider_name='simulation' and is_live=False.
"""
import time
import math
import random
import uuid
import asyncio
from typing import Optional
from app.providers.base import (
    BaseVirtualizationProvider,
    NodeTelemetry,
    VMTelemetry,
    ClusterState,
    MigrationPlan,
    MigrationTaskStatus,
    MigrationState,
    ProviderConnectionResult
)


class SimulationProvider(BaseVirtualizationProvider):
    def __init__(self):
        self._connected = True
        self._step_counter = 0
        self._nodes: dict[str, NodeTelemetry] = {
            "node-01": NodeTelemetry(
                id="node-01",
                name="hv-compute-01.mgmt",
                status="online",
                cpu_cores=32,
                cpu_percent=78.5,
                ram_total_mb=131072.0,
                ram_used_mb=105000.0,
                ram_percent=80.1,
                net_rx_kbps=4520.0,
                net_tx_kbps=6120.0,
                disk_total_gb=2000.0,
                disk_used_gb=1250.0,
                shared_storage_accessible=True,
                quorum_healthy=True,
                active_vms=["vm-101", "vm-102", "vm-104"]
            ),
            "node-02": NodeTelemetry(
                id="node-02",
                name="hv-compute-02.mgmt",
                status="online",
                cpu_cores=32,
                cpu_percent=42.0,
                ram_total_mb=131072.0,
                ram_used_mb=52428.0,
                ram_percent=40.0,
                net_rx_kbps=1820.0,
                net_tx_kbps=1940.0,
                disk_total_gb=2000.0,
                disk_used_gb=890.0,
                shared_storage_accessible=True,
                quorum_healthy=True,
                active_vms=["vm-103", "vm-105"]
            ),
            "node-03": NodeTelemetry(
                id="node-03",
                name="hv-compute-03.mgmt",
                status="online",
                cpu_cores=32,
                cpu_percent=26.3,
                ram_total_mb=131072.0,
                ram_used_mb=34000.0,
                ram_percent=25.9,
                net_rx_kbps=850.0,
                net_tx_kbps=910.0,
                disk_total_gb=2000.0,
                disk_used_gb=620.0,
                shared_storage_accessible=True,
                quorum_healthy=True,
                active_vms=["vm-106"]
            )
        }

        self._vms: dict[str, VMTelemetry] = {
            "vm-101": VMTelemetry(
                vmid="vm-101",
                name="core-db-primary",
                node_id="node-01",
                status="running",
                cpu_cores=8,
                cpu_percent=68.2,
                ram_allocated_mb=32768.0,
                ram_used_mb=28400.0,
                ram_percent=86.7,
                net_io_kbps=3200.0,
                disk_allocated_gb=250.0,
                sla_priority="critical",
                sla_max_cpu_percent=80.0,
                uptime_seconds=86400 * 12
            ),
            "vm-102": VMTelemetry(
                vmid="vm-102",
                name="analytics-pipeline-01",
                node_id="node-01",
                status="running",
                cpu_cores=6,
                cpu_percent=74.5,
                ram_allocated_mb=16384.0,
                ram_used_mb=14200.0,
                ram_percent=86.6,
                net_io_kbps=2100.0,
                disk_allocated_gb=120.0,
                sla_priority="standard",
                sla_max_cpu_percent=85.0,
                uptime_seconds=86400 * 4
            ),
            "vm-103": VMTelemetry(
                vmid="vm-103",
                name="api-gateway-edge",
                node_id="node-02",
                status="running",
                cpu_cores=4,
                cpu_percent=34.1,
                ram_allocated_mb=8192.0,
                ram_used_mb=4100.0,
                ram_percent=50.0,
                net_io_kbps=1450.0,
                disk_allocated_gb=40.0,
                sla_priority="high",
                sla_max_cpu_percent=75.0,
                uptime_seconds=86400 * 21
            ),
            "vm-104": VMTelemetry(
                vmid="vm-104",
                name="in-memory-cache-01",
                node_id="node-01",
                status="running",
                cpu_cores=6,
                cpu_percent=62.4,
                ram_allocated_mb=24576.0,
                ram_used_mb=21000.0,
                ram_percent=85.4,
                net_io_kbps=1800.0,
                disk_allocated_gb=60.0,
                sla_priority="standard",
                sla_max_cpu_percent=85.0,
                uptime_seconds=86400 * 6
            ),
            "vm-105": VMTelemetry(
                vmid="vm-105",
                name="batch-worker-pool",
                node_id="node-02",
                status="running",
                cpu_cores=4,
                cpu_percent=28.0,
                ram_allocated_mb=12288.0,
                ram_used_mb=6800.0,
                ram_percent=55.3,
                net_io_kbps=450.0,
                disk_allocated_gb=80.0,
                sla_priority="batch",
                sla_max_cpu_percent=90.0,
                uptime_seconds=86400 * 2
            ),
            "vm-106": VMTelemetry(
                vmid="vm-106",
                name="telemetry-collector-02",
                node_id="node-03",
                status="running",
                cpu_cores=2,
                cpu_percent=18.6,
                ram_allocated_mb=4096.0,
                ram_used_mb=2200.0,
                ram_percent=53.7,
                net_io_kbps=820.0,
                disk_allocated_gb=30.0,
                sla_priority="standard",
                sla_max_cpu_percent=80.0,
                uptime_seconds=86400 * 9
            )
        }

        self._active_tasks: dict[str, MigrationTaskStatus] = {}

    async def test_connection(self) -> ProviderConnectionResult:
        nodes = await self.discover_nodes()
        vms = await self.discover_vms()
        return ProviderConnectionResult(
            provider="simulation",
            status="CONNECTED",
            latency_ms=0.4,
            hypervisor_version="SimEngine-v1.0 (In-Memory Topology Emulator)",
            node_count=len(nodes),
            vm_count=len(vms),
            message="Simulation provider active. 3 simulated nodes and 6 workloads available."
        )

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    async def discover_nodes(self) -> list[NodeTelemetry]:
        self._drift_telemetry()
        return list(self._nodes.values())

    async def discover_vms(self) -> list[VMTelemetry]:
        return list(self._vms.values())

    async def collect_telemetry(self) -> ClusterState:
        self._drift_telemetry()
        return ClusterState(
            is_live=False,  # Explicitly false: this is simulation
            connected=self._connected,
            provider_name="simulation",
            timestamp=time.time(),
            nodes=self._nodes,
            vms=self._vms,
            error_message=None if self._connected else "SIMULATION_DISCONNECTED"
        )

    async def inspect_vm_state(self, vm_id: str) -> Optional[VMTelemetry]:
        return self._vms.get(vm_id)

    def _drift_telemetry(self):
        """Simulate realistic telemetry fluctuations and load migration impacts."""
        self._step_counter += 1
        t = self._step_counter * 0.1

        for vmid, vm in self._vms.items():
            if vm.status == "running":
                osc = math.sin(t + hash(vmid) % 10) * 4.0
                noise = random.uniform(-1.5, 1.5)
                vm.cpu_percent = max(5.0, min(95.0, round(vm.cpu_percent + (osc * 0.08) + noise, 1)))
                vm.net_io_kbps = max(50.0, round(vm.net_io_kbps + random.uniform(-30, 35), 1))
            elif vm.status == "migrating":
                vm.net_io_kbps = round(random.uniform(45000.0, 65000.0), 1)

        for node_id, node in self._nodes.items():
            hosted_vms = [v for v in self._vms.values() if v.node_id == node_id and v.status != "migrating"]
            node.active_vms = [v.vmid for v in hosted_vms]
            
            if hosted_vms:
                total_vm_cpu_cores = sum(v.cpu_cores * (v.cpu_percent / 100.0) for v in hosted_vms)
                node_cpu_load = (total_vm_cpu_cores / node.cpu_cores) * 100.0
                node.cpu_percent = max(8.0, min(98.0, round(node_cpu_load + random.uniform(-1.0, 1.0), 1)))

                total_ram_used = sum(v.ram_used_mb for v in hosted_vms)
                node.ram_used_mb = total_ram_used + 4096.0  # Base OS overhead
                node.ram_percent = max(10.0, min(98.0, round((node.ram_used_mb / node.ram_total_mb) * 100.0, 1)))
            else:
                node.cpu_percent = round(random.uniform(4.0, 8.0), 1)
                node.ram_used_mb = 4096.0
                node.ram_percent = round((4096.0 / node.ram_total_mb) * 100.0, 1)

    async def validate_migration(self, vm_id: str, target_node: str) -> tuple[bool, str]:
        if vm_id not in self._vms:
            return False, f"VM '{vm_id}' not found in cluster."
        if target_node not in self._nodes:
            return False, f"Target node '{target_node}' does not exist."
        
        vm = self._vms[vm_id]
        if vm.node_id == target_node:
            return False, f"VM '{vm_id}' is already hosted on node '{target_node}'."
        if vm.status != "running":
            return False, f"VM '{vm_id}' is not in running state (current: {vm.status})."

        target = self._nodes[target_node]
        if target.status != "online":
            return False, f"Target node '{target_node}' is not online."
        
        available_ram = target.ram_total_mb - target.ram_used_mb
        if available_ram < vm.ram_allocated_mb:
            return False, f"Insufficient memory on '{target_node}'. Free: {available_ram:.0f}MB, Required: {vm.ram_allocated_mb:.0f}MB."

        return True, "Validation successful."

    async def plan_migration(self, vm_id: str, target_node: str, reason: str = "Rebalance") -> MigrationPlan:
        if vm_id not in self._vms:
            raise KeyError(f"VM '{vm_id}' not found.")
        source = self._vms[vm_id].node_id
        return MigrationPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            vm_id=vm_id,
            source_node=source,
            target_node=target_node,
            reason=reason,
            created_at=time.time(),
            recommended_by="MANUAL"
        )

    async def execute_migration(self, plan: MigrationPlan) -> str:
        valid, msg = await self.validate_migration(plan.vm_id, plan.target_node)
        if not valid:
            raise ValueError(f"Hypervisor pre-validation failed: {msg}")

        task_id = f"sim-task-{uuid.uuid4().hex[:8]}"
        now = time.time()
        
        self._vms[plan.vm_id].status = "migrating"

        status = MigrationTaskStatus(
            task_id=task_id,
            plan_id=plan.plan_id,
            vm_id=plan.vm_id,
            source_node=plan.source_node,
            target_node=plan.target_node,
            state="PREPARING",
            progress_percent=5.0,
            started_at=now,
            updated_at=now
        )
        self._active_tasks[task_id] = status
        
        asyncio.create_task(self._run_simulated_migration(task_id, plan))
        return task_id

    async def _run_simulated_migration(self, task_id: str, plan: MigrationPlan):
        stages: list[tuple[MigrationState, float, float]] = [
            ("PREPARING", 15.0, 0.7),
            ("VALIDATING", 30.0, 0.7),
            ("MIGRATING", 55.0, 1.0),
            ("MIGRATING", 80.0, 1.0),
            ("MONITORING", 92.0, 0.7),
            ("VERIFYING", 98.0, 0.7)
        ]

        try:
            for state_name, progress, delay in stages:
                await asyncio.sleep(delay)
                if task_id in self._active_tasks:
                    self._active_tasks[task_id].state = state_name
                    self._active_tasks[task_id].progress_percent = progress
                    self._active_tasks[task_id].updated_at = time.time()

            await asyncio.sleep(0.5)
            
            # Transfer placement
            vm = self._vms[plan.vm_id]
            vm.node_id = plan.target_node
            vm.status = "running"
            vm.last_migrated_at = time.time()
            vm.migration_count += 1

            # Update active node VM lists
            if plan.vm_id in self._nodes[plan.source_node].active_vms:
                self._nodes[plan.source_node].active_vms.remove(plan.vm_id)
            if plan.vm_id not in self._nodes[plan.target_node].active_vms:
                self._nodes[plan.target_node].active_vms.append(plan.vm_id)

            now = time.time()
            task = self._active_tasks[task_id]
            task.state = "VERIFIED"
            task.progress_percent = 100.0
            task.updated_at = now
            task.completed_at = now
            task.verified_at = now
            task.verification_details = {
                "destination_confirmed": True,
                "current_node": vm.node_id,
                "vm_health": "running",
                "round_trip_latency_ms": 0.38,
                "downtime_ms": 12.4
            }

        except Exception as e:
            if task_id in self._active_tasks:
                self._active_tasks[task_id].state = "FAILED"
                self._active_tasks[task_id].error = str(e)
            if plan.vm_id in self._vms:
                self._vms[plan.vm_id].status = "running"

    async def monitor_migration_task(self, task_id: str) -> MigrationTaskStatus:
        if task_id not in self._active_tasks:
            raise KeyError(f"Task '{task_id}' not found.")
        return self._active_tasks[task_id]

    async def verify_placement(self, vm_id: str, expected_node: str) -> tuple[bool, str]:
        if vm_id not in self._vms:
            return False, f"VM '{vm_id}' does not exist in cluster."
        vm = self._vms[vm_id]
        if vm.node_id != expected_node:
            return False, f"Placement mismatch: VM '{vm_id}' resides on '{vm.node_id}', expected '{expected_node}'."
        return True, f"Placement verified: VM '{vm_id}' resides on node '{expected_node}'."

    async def verify_vm_health(self, vm_id: str) -> tuple[bool, str]:
        if vm_id not in self._vms:
            return False, f"VM '{vm_id}' does not exist."
        vm = self._vms[vm_id]
        if vm.status != "running":
            return False, f"VM health check failed: status is '{vm.status}', expected 'running'."
        return True, f"VM '{vm_id}' is healthy and running."
