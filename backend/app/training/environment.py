"""
Offline Gymnasium Reinforcement Learning Environment for VMotion AI.
Complies with 103-dimensional observation space and 7-action discrete space.
Simulates cluster telemetry dynamics, SLA constraints, load distribution, and migration costs.
"""
import time
import math
import copy
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, List, Tuple, Optional, Any

from app.providers.base import ClusterState, NodeTelemetry, VMTelemetry
from app.adapter.observation import ObservationAdapter


SCENARIO_TYPES: List[str] = [
    "NORMAL",
    "CPU_HOTSPOT",
    "RAM_HOTSPOT",
    "NETWORK_HOTSPOT",
    "SLA_CRITICAL",
    "MIXED_OVERLOAD",
    "EXPENSIVE_MIGRATION",
    "UNEVEN_CLUSTER",
    "RAPID_LOAD_CHANGE",
    "MIGRATION_COOLDOWN_PRESSURE",
]

SCENARIO_SPLITS: Dict[str, List[str]] = {
    "TRAIN": ["NORMAL", "CPU_HOTSPOT", "RAM_HOTSPOT", "MIXED_OVERLOAD"],
    "VALIDATION": ["SLA_CRITICAL", "UNEVEN_CLUSTER", "RAPID_LOAD_CHANGE"],
    "TEST": ["NETWORK_HOTSPOT", "EXPENSIVE_MIGRATION", "MIGRATION_COOLDOWN_PRESSURE"],
}


class VMotionEnv(gym.Env):
    """
    Gymnasium environment simulating live VM migration control across a 3-node cluster.

    Observation Space: Box(103,), values normalized [0.0, 1.0] (with node_idx in [-1.0, 1.0])
    Action Space: Discrete(7)
        - 0: No-Op (keep current placement)
        - 1: Migrate VM-101 to selected least-loaded destination node
        - 2: Migrate VM-102 to selected least-loaded destination node
        - 3: Migrate VM-103 to selected least-loaded destination node
        - 4: Migrate VM-104 to selected least-loaded destination node
        - 5: Migrate VM-105 to selected least-loaded destination node
        - 6: Migrate VM-106 to selected least-loaded destination node
    """
    metadata = {"render_modes": ["ansi"]}

    def __init__(
        self,
        max_steps: int = 100,
        cooldown_seconds: float = 60.0,
        step_simulated_seconds: float = 15.0,
        scenario: str = "NORMAL",
        scenario_distribution: Optional[Dict[str, float]] = None,
        curriculum_config: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None
    ):
        super().__init__()
        self.max_steps = max_steps
        self.base_cooldown_seconds = cooldown_seconds
        self.cooldown_seconds = cooldown_seconds
        self.step_simulated_seconds = step_simulated_seconds
        self.scenario = scenario
        self.scenario_distribution = scenario_distribution
        self.curriculum_config = curriculum_config
        self.total_episodes_started = 0
        self.total_steps_executed = 0
        self.scenario_stats: Dict[str, Dict[str, int]] = {
            sc: {"episodes": 0, "steps": 0} for sc in SCENARIO_TYPES
        }
        self.adapter = ObservationAdapter(node_ids=["node-01", "node-02", "node-03"], max_vms=6)

        # Spaces
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(103,),
            dtype=np.float32
        )
        self.action_space = spaces.Discrete(7)

        # Internal state
        self.current_step = 0
        self.simulated_time = 0.0
        self.cluster: Optional[ClusterState] = None
        self.rng = np.random.default_rng(seed)

        # Cumulative episode metrics
        self.ep_migrations = 0
        self.ep_no_ops = 0
        self.ep_invalid_actions = 0
        self.ep_sla_breaches = 0
        self.ep_overloaded_steps = 0
        self.ep_unique_vms: set[str] = set()
        self.ep_unique_destinations: set[str] = set()
        self.ep_reward_breakdown: Dict[str, float] = {
            "fairness": 0.0,
            "cpu_std": 0.0,
            "stability": 0.0,
            "sla": 0.0,
            "overload": 0.0,
            "migration": 0.0,
            "invalid": 0.0,
            "total": 0.0,
        }

        if seed is not None:
            self.reset(seed=seed)

    def _generate_initial_cluster(self) -> ClusterState:
        """Generates a randomized cluster state according to the active scenario."""
        now = self.simulated_time
        scenario = self.scenario.upper()

        if scenario == "CPU_HOTSPOT":
            # Node 01 heavily overloaded (>85%), other nodes have compute headroom
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=92.0 + self.rng.uniform(-2.0, 5.0),
                    ram_percent=68.0, ram_total_mb=32768.0, ram_used_mb=22282.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=18500.0, net_tx_kbps=22000.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=26.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=38.0, ram_total_mb=32768.0, ram_used_mb=12450.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=4200.0, net_tx_kbps=5100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=16.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=24.0, ram_total_mb=32768.0, ram_used_mb=7864.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=2100.0, net_tx_kbps=3200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=90.0 + self.rng.uniform(-3.0, 4.0),
                    ram_percent=75.0, ram_allocated_mb=8192.0, ram_used_mb=6144.0,
                    net_io_kbps=16000.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=78.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=60.0, ram_allocated_mb=8192.0, ram_used_mb=4915.0,
                    net_io_kbps=9500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=68.0 + self.rng.uniform(-5.0, 5.0),
                    ram_percent=45.0, ram_allocated_mb=4096.0, ram_used_mb=1843.0,
                    net_io_kbps=3600.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=28.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=55.0, ram_allocated_mb=8192.0, ram_used_mb=4505.0,
                    net_io_kbps=11000.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=22.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=35.0, ram_allocated_mb=4096.0, ram_used_mb=1433.0,
                    net_io_kbps=3800.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=18.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=28.0, ram_allocated_mb=4096.0, ram_used_mb=1146.0,
                    net_io_kbps=2200.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "RAM_HOTSPOT":
            # Node 02 has 90% RAM used (only 3268 MB free) - 8192 MB VMs cannot fit on Node 02
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=76.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=68.0, ram_total_mb=32768.0, ram_used_mb=22282.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=14500.0, net_tx_kbps=18200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=30.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=90.0, ram_total_mb=32768.0, ram_used_mb=29500.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=6200.0, net_tx_kbps=8100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=22.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=25.0, ram_total_mb=32768.0, ram_used_mb=8192.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=3400.0, net_tx_kbps=4500.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=82.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=72.0, ram_allocated_mb=8192.0, ram_used_mb=5898.0,
                    net_io_kbps=12400.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=48.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=55.0, ram_allocated_mb=8192.0, ram_used_mb=4505.0,
                    net_io_kbps=8500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=38.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=3200.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=32.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=85.0, ram_allocated_mb=16384.0, ram_used_mb=13926.0,
                    net_io_kbps=14200.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=26.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=78.0, ram_allocated_mb=12288.0, ram_used_mb=9584.0,
                    net_io_kbps=4100.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=20.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=30.0, ram_allocated_mb=4096.0, ram_used_mb=1228.0,
                    net_io_kbps=2800.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "NETWORK_HOTSPOT":
            # Extreme network throughput saturation on Node 01
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=72.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=65.0, ram_total_mb=32768.0, ram_used_mb=21299.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=82000.0, net_tx_kbps=94000.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=35.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=42.0, ram_total_mb=32768.0, ram_used_mb=13762.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=4800.0, net_tx_kbps=6200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=24.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=28.0, ram_total_mb=32768.0, ram_used_mb=9175.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=3100.0, net_tx_kbps=3900.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=78.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=70.0, ram_allocated_mb=8192.0, ram_used_mb=5734.0,
                    net_io_kbps=58000.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=45.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=55.0, ram_allocated_mb=8192.0, ram_used_mb=4505.0,
                    net_io_kbps=42000.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=36.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=18000.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=34.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=65.0, ram_allocated_mb=8192.0, ram_used_mb=5324.0,
                    net_io_kbps=8500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=26.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=38.0, ram_allocated_mb=4096.0, ram_used_mb=1556.0,
                    net_io_kbps=2500.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=22.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=30.0, ram_allocated_mb=4096.0, ram_used_mb=1228.0,
                    net_io_kbps=1800.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "SLA_CRITICAL":
            # Workloads operating razor-close to SLA limits
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=83.0 + self.rng.uniform(-2.0, 3.0),
                    ram_percent=70.0, ram_total_mb=32768.0, ram_used_mb=22937.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=15500.0, net_tx_kbps=19200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=52.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=45.0, ram_total_mb=32768.0, ram_used_mb=14745.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=7500.0, net_tx_kbps=9100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=20.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=26.0, ram_total_mb=32768.0, ram_used_mb=8519.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=3100.0, net_tx_kbps=4100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=84.5 + self.rng.uniform(-0.5, 1.0),
                    ram_percent=74.0, ram_allocated_mb=8192.0, ram_used_mb=6062.0,
                    net_io_kbps=13200.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=79.2 + self.rng.uniform(-0.5, 1.2),
                    ram_percent=58.0, ram_allocated_mb=8192.0, ram_used_mb=4751.0,
                    net_io_kbps=9100.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=42.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=42.0, ram_allocated_mb=4096.0, ram_used_mb=1720.0,
                    net_io_kbps=3400.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=78.5 + self.rng.uniform(-0.5, 1.0),
                    ram_percent=68.0, ram_allocated_mb=8192.0, ram_used_mb=5570.0,
                    net_io_kbps=14800.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=74.3 + self.rng.uniform(-0.5, 1.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=4300.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=20.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=28.0, ram_allocated_mb=4096.0, ram_used_mb=1146.0,
                    net_io_kbps=2500.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "MIXED_OVERLOAD":
            # Dual-node saturation: Node 01 and Node 02 are both overloaded
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=89.0 + self.rng.uniform(-2.0, 3.0),
                    ram_percent=76.0, ram_total_mb=32768.0, ram_used_mb=24903.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=18200.0, net_tx_kbps=21000.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=86.0 + self.rng.uniform(-2.0, 3.0),
                    ram_percent=82.0, ram_total_mb=32768.0, ram_used_mb=26869.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=15400.0, net_tx_kbps=17600.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=18.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=25.0, ram_total_mb=32768.0, ram_used_mb=8192.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=2500.0, net_tx_kbps=3400.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=85.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=75.0, ram_allocated_mb=8192.0, ram_used_mb=6144.0,
                    net_io_kbps=15500.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=74.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=60.0, ram_allocated_mb=8192.0, ram_used_mb=4915.0,
                    net_io_kbps=9800.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=55.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=45.0, ram_allocated_mb=4096.0, ram_used_mb=1843.0,
                    net_io_kbps=3800.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=82.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=80.0, ram_allocated_mb=12288.0, ram_used_mb=9830.0,
                    net_io_kbps=16000.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=72.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=75.0, ram_allocated_mb=8192.0, ram_used_mb=6144.0,
                    net_io_kbps=4500.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=18.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=25.0, ram_allocated_mb=4096.0, ram_used_mb=1024.0,
                    net_io_kbps=2200.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "EXPENSIVE_MIGRATION":
            # Workloads with large memory allocations
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=78.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=78.0, ram_total_mb=32768.0, ram_used_mb=25559.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=15500.0, net_tx_kbps=18200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=35.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=45.0, ram_total_mb=32768.0, ram_used_mb=14745.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=6500.0, net_tx_kbps=8500.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=22.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=30.0, ram_total_mb=32768.0, ram_used_mb=9830.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=3600.0, net_tx_kbps=4800.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=82.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=75.0, ram_allocated_mb=16384.0, ram_used_mb=12288.0,
                    net_io_kbps=13000.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=48.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=65.0, ram_allocated_mb=12288.0, ram_used_mb=7987.0,
                    net_io_kbps=9000.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=38.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=3400.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=36.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=70.0, ram_allocated_mb=12288.0, ram_used_mb=8601.0,
                    net_io_kbps=14500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=28.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=4200.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=22.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=35.0, ram_allocated_mb=8192.0, ram_used_mb=2867.0,
                    net_io_kbps=2900.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        elif scenario == "UNEVEN_CLUSTER":
            # Extreme placement skew: 5 VMs on node-01, 1 on node-02, 0 on node-03
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=94.0 + self.rng.uniform(-2.0, 3.0),
                    ram_percent=88.0, ram_total_mb=32768.0, ram_used_mb=28835.0,
                    disk_total_gb=1000.0, disk_used_gb=520.0,
                    net_rx_kbps=28500.0, net_tx_kbps=33000.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103", "vm-104", "vm-105"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=18.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=20.0, ram_total_mb=32768.0, ram_used_mb=6553.0,
                    disk_total_gb=1000.0, disk_used_gb=250.0,
                    net_rx_kbps=3200.0, net_tx_kbps=4100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=5.0,
                    ram_percent=10.0, ram_total_mb=32768.0, ram_used_mb=3276.0,
                    disk_total_gb=1000.0, disk_used_gb=150.0,
                    net_rx_kbps=800.0, net_tx_kbps=1100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=[]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=82.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=72.0, ram_allocated_mb=8192.0, ram_used_mb=5898.0,
                    net_io_kbps=12400.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=46.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=55.0, ram_allocated_mb=8192.0, ram_used_mb=4505.0,
                    net_io_kbps=8500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=38.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=3200.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-01", status="running",
                    cpu_percent=35.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=65.0, ram_allocated_mb=8192.0, ram_used_mb=5324.0,
                    net_io_kbps=14200.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-01", status="running",
                    cpu_percent=28.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=38.0, ram_allocated_mb=4096.0, ram_used_mb=1556.0,
                    net_io_kbps=4100.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-02", status="running",
                    cpu_percent=22.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=30.0, ram_allocated_mb=4096.0, ram_used_mb=1228.0,
                    net_io_kbps=2800.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        else:
            # "NORMAL", "RAPID_LOAD_CHANGE", "MIGRATION_COOLDOWN_PRESSURE"
            nodes = {
                "node-01": NodeTelemetry(
                    id="node-01", name="pve-node-01", status="online",
                    cpu_percent=78.0 + self.rng.uniform(-5.0, 10.0),
                    ram_percent=68.0, ram_total_mb=32768.0, ram_used_mb=22282.0,
                    disk_total_gb=1000.0, disk_used_gb=420.0,
                    net_rx_kbps=14500.0, net_tx_kbps=18200.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-101", "vm-102", "vm-103"]
                ),
                "node-02": NodeTelemetry(
                    id="node-02", name="pve-node-02", status="online",
                    cpu_percent=32.0 + self.rng.uniform(-8.0, 8.0),
                    ram_percent=42.0, ram_total_mb=32768.0, ram_used_mb=13762.0,
                    disk_total_gb=1000.0, disk_used_gb=350.0,
                    net_rx_kbps=6200.0, net_tx_kbps=8100.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-104", "vm-105"]
                ),
                "node-03": NodeTelemetry(
                    id="node-03", name="pve-node-03", status="online",
                    cpu_percent=22.0 + self.rng.uniform(-5.0, 5.0),
                    ram_percent=28.0, ram_total_mb=32768.0, ram_used_mb=9175.0,
                    disk_total_gb=1000.0, disk_used_gb=280.0,
                    net_rx_kbps=3400.0, net_tx_kbps=4500.0,
                    cpu_cores=16, quorum_healthy=True, shared_storage_accessible=True,
                    active_vms=["vm-106"]
                ),
            }
            vms = {
                "vm-101": VMTelemetry(
                    vmid="vm-101", name="prod-api-gateway", node_id="node-01", status="running",
                    cpu_percent=82.0 + self.rng.uniform(-5.0, 8.0),
                    ram_percent=72.0, ram_allocated_mb=8192.0, ram_used_mb=5898.0,
                    net_io_kbps=12400.0, sla_priority="critical", sla_max_cpu_percent=85.0,
                    last_migrated_at=now - 120.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-102": VMTelemetry(
                    vmid="vm-102", name="order-processing-svc", node_id="node-01", status="running",
                    cpu_percent=46.0 + self.rng.uniform(-6.0, 6.0),
                    ram_percent=55.0, ram_allocated_mb=8192.0, ram_used_mb=4505.0,
                    net_io_kbps=8500.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 150.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-103": VMTelemetry(
                    vmid="vm-103", name="batch-worker-01", node_id="node-01", status="running",
                    cpu_percent=38.0 + self.rng.uniform(-8.0, 8.0),
                    ram_percent=40.0, ram_allocated_mb=4096.0, ram_used_mb=1638.0,
                    net_io_kbps=3200.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 300.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-104": VMTelemetry(
                    vmid="vm-104", name="redis-cache-cluster", node_id="node-02", status="running",
                    cpu_percent=35.0 + self.rng.uniform(-5.0, 5.0),
                    ram_percent=65.0, ram_allocated_mb=8192.0, ram_used_mb=5324.0,
                    net_io_kbps=14200.0, sla_priority="high", sla_max_cpu_percent=80.0,
                    last_migrated_at=now - 200.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-105": VMTelemetry(
                    vmid="vm-105", name="auth-service", node_id="node-02", status="running",
                    cpu_percent=28.0 + self.rng.uniform(-4.0, 4.0),
                    ram_percent=38.0, ram_allocated_mb=4096.0, ram_used_mb=1556.0,
                    net_io_kbps=4100.0, sla_priority="standard", sla_max_cpu_percent=75.0,
                    last_migrated_at=now - 180.0, migration_count=0, uptime_seconds=86400.0
                ),
                "vm-106": VMTelemetry(
                    vmid="vm-106", name="telemetry-pipeline", node_id="node-03", status="running",
                    cpu_percent=22.0 + self.rng.uniform(-3.0, 3.0),
                    ram_percent=30.0, ram_allocated_mb=4096.0, ram_used_mb=1228.0,
                    net_io_kbps=2800.0, sla_priority="batch", sla_max_cpu_percent=90.0,
                    last_migrated_at=now - 250.0, migration_count=0, uptime_seconds=86400.0
                ),
            }

        return ClusterState(
            is_live=False,
            connected=True,
            provider_name="simulation",
            timestamp=now,
            nodes=nodes,
            vms=vms
        )

    def action_masks(self) -> np.ndarray:
        """
        Returns boolean mask of valid actions for MaskablePPO.
        Action 0 (No-Op) is always valid.
        Actions 1..6 represent VMs 0..5 in sorted order.
        """
        masks = [True]  # Action 0 = No-Op
        if not self.cluster:
            return np.array([True] + [False] * 6, dtype=bool)

        sorted_vms = sorted(self.cluster.vms.values(), key=lambda v: v.vmid)[:6]
        now = self.simulated_time

        for vm in sorted_vms:
            elapsed = (now - vm.last_migrated_at) if vm.last_migrated_at else 999.0
            is_in_cooldown = elapsed < self.cooldown_seconds
            is_running = vm.status == "running"
            
            # Must have at least one other online node with available RAM
            other_nodes = [
                n for n in self.cluster.nodes.values()
                if n.id != vm.node_id and n.status == "online" and (n.ram_total_mb - n.ram_used_mb) >= vm.ram_allocated_mb
            ]

            valid = is_running and (not is_in_cooldown) and (len(other_nodes) > 0)
            masks.append(valid)

        while len(masks) < 7:
            masks.append(False)

        return np.array(masks, dtype=bool)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        self.total_episodes_started += 1

        if options and "scenario" in options:
            self.scenario = options["scenario"]
        elif self.curriculum_config and self.curriculum_config.get("enabled"):
            current_step = self.total_steps_executed
            dist = None
            for stage in self.curriculum_config.get("stages", []):
                if current_step < stage.get("until_step", float("inf")):
                    dist = stage.get("distribution")
                    break
            if dist:
                scenarios = list(dist.keys())
                weights = np.array(list(dist.values()), dtype=np.float64)
                weights /= np.sum(weights)
                self.scenario = str(self.rng.choice(scenarios, p=weights))
        elif self.scenario_distribution:
            scenarios = list(self.scenario_distribution.keys())
            weights = np.array(list(self.scenario_distribution.values()), dtype=np.float64)
            weights /= np.sum(weights)
            self.scenario = str(self.rng.choice(scenarios, p=weights))

        if self.scenario in self.scenario_stats:
            self.scenario_stats[self.scenario]["episodes"] += 1

        # Apply scenario-specific parameter adaptations
        if self.scenario == "MIGRATION_COOLDOWN_PRESSURE":
            self.cooldown_seconds = 120.0
        else:
            self.cooldown_seconds = self.base_cooldown_seconds

        self.current_step = 0
        self.simulated_time = 1700000000.0  # Stable baseline timestamp
        self.cluster = self._generate_initial_cluster()

        # Cumulative episode trackers
        self.ep_migrations = 0
        self.ep_no_ops = 0
        self.ep_invalid_actions = 0
        self.ep_sla_breaches = 0
        self.ep_overloaded_steps = 0
        self.ep_unique_vms = set()
        self.ep_unique_destinations = set()
        self.ep_reward_breakdown = {
            "fairness": 0.0,
            "cpu_std": 0.0,
            "stability": 0.0,
            "sla": 0.0,
            "overload": 0.0,
            "migration": 0.0,
            "invalid": 0.0,
            "total": 0.0,
        }

        obs = self.adapter.extract_features(self.cluster)
        info = {
            "step": self.current_step,
            "action_mask": self.action_masks(),
            "scenario": self.scenario
        }
        return obs, info

    def get_training_scenario_summary(self) -> Dict[str, Any]:
        """Returns metadata on scenario episodes and steps executed during training."""
        total_ep = sum(s["episodes"] for s in self.scenario_stats.values())
        total_st = sum(s["steps"] for s in self.scenario_stats.values())
        summary = {}
        for sc, stats in self.scenario_stats.items():
            if stats["episodes"] > 0 or stats["steps"] > 0:
                summary[sc] = {
                    "episodes": stats["episodes"],
                    "steps": stats["steps"],
                    "percentage_episodes": round((stats["episodes"] / max(1, total_ep)) * 100.0, 2),
                    "percentage_steps": round((stats["steps"] / max(1, total_st)) * 100.0, 2),
                }
        return {
            "total_episodes": total_ep,
            "total_steps": total_st,
            "scenarios": summary
        }

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        assert self.action_space.contains(action), f"Invalid action {action}"
        self.current_step += 1
        self.total_steps_executed += 1
        if self.scenario in self.scenario_stats:
            self.scenario_stats[self.scenario]["steps"] += 1
        self.simulated_time += self.step_simulated_seconds
        self.cluster.timestamp = self.simulated_time

        action_executed = "NO_OP"
        action_valid = True
        migrated_vm_id = None
        target_node_id = None

        step_migration_penalty = 0.0
        step_invalid_penalty = 0.0

        # Scenario parameters
        migration_unit_penalty = -1.5 if self.scenario == "EXPENSIVE_MIGRATION" else -0.8
        load_variance = 6.5 if self.scenario == "RAPID_LOAD_CHANGE" else 2.5

        sorted_vms = sorted(self.cluster.vms.values(), key=lambda v: v.vmid)[:6]
        valid_masks = self.action_masks()

        if action > 0:
            vm_idx = action - 1
            if not valid_masks[action]:
                # Invalid action penalty
                action_valid = False
                step_invalid_penalty = -10.0
            else:
                vm = sorted_vms[vm_idx]
                migrated_vm_id = vm.vmid
                src_node_id = vm.node_id

                # Select destination node: least loaded alternative node with RAM capacity
                candidates = [
                    n for n in self.cluster.nodes.values()
                    if n.id != src_node_id and n.status == "online" and (n.ram_total_mb - n.ram_used_mb) >= vm.ram_allocated_mb
                ]
                if candidates:
                    target_node = min(candidates, key=lambda n: n.cpu_percent)
                    target_node_id = target_node.id
                    action_executed = f"MIGRATE {vm.vmid} -> {target_node_id}"

                    # Update source node
                    src_node = self.cluster.nodes[src_node_id]
                    if vm.vmid in src_node.active_vms:
                        src_node.active_vms.remove(vm.vmid)
                    src_node.ram_used_mb = max(0.0, src_node.ram_used_mb - vm.ram_allocated_mb)
                    src_node.ram_percent = (src_node.ram_used_mb / src_node.ram_total_mb) * 100.0

                    # Update target node
                    target_node.active_vms.append(vm.vmid)
                    target_node.ram_used_mb += vm.ram_allocated_mb
                    target_node.ram_percent = (target_node.ram_used_mb / target_node.ram_total_mb) * 100.0

                    # Update VM
                    vm.node_id = target_node_id
                    vm.last_migrated_at = self.simulated_time
                    vm.migration_count += 1

                    # Migration cost penalty
                    step_migration_penalty = migration_unit_penalty
                else:
                    action_valid = False
                    step_invalid_penalty = -5.0

        # Simulate natural load fluctuations and recalculate node CPU loads
        for vm in self.cluster.vms.values():
            fluctuation = float(self.rng.normal(0.0, load_variance))
            vm.cpu_percent = float(np.clip(vm.cpu_percent + fluctuation, 10.0, 95.0))

        for nid, node in self.cluster.nodes.items():
            hosted_vms = [v for v in self.cluster.vms.values() if v.node_id == nid]
            if hosted_vms:
                base_overhead = 8.0
                computed_cpu = base_overhead + sum(v.cpu_percent * 0.45 for v in hosted_vms)
                node.cpu_percent = float(np.clip(computed_cpu, 5.0, 100.0))
            else:
                node.cpu_percent = 5.0  # Idle host overhead

        # Compute cluster-wide balance metrics
        node_cpus = [n.cpu_percent / 100.0 for n in self.cluster.nodes.values()]
        cpu_arr = np.array(node_cpus)
        cpu_std = float(np.std(cpu_arr))

        # Jain's fairness index
        sum_c = np.sum(cpu_arr)
        sum_sq = np.sum(cpu_arr ** 2)
        jains = float((sum_c ** 2) / (len(cpu_arr) * sum_sq)) if sum_sq > 0 else 1.0

        # Individual reward terms
        step_fairness_reward = 2.5 * jains
        step_cpu_std_penalty = -1.5 * cpu_std
        step_stability_bonus = 1.0 if (action == 0 and cpu_std < 0.12) else 0.0

        sla_breaches = 0
        for vm in self.cluster.vms.values():
            if vm.cpu_percent > vm.sla_max_cpu_percent:
                sla_breaches += 1
        step_sla_penalty = -2.0 * sla_breaches

        overloaded_nodes = [nid for nid, n in self.cluster.nodes.items() if n.cpu_percent > 85.0]
        step_overload_penalty = -4.0 * len(overloaded_nodes)

        total_step_reward = (
            step_fairness_reward
            + step_cpu_std_penalty
            + step_stability_bonus
            + step_sla_penalty
            + step_overload_penalty
            + step_migration_penalty
            + step_invalid_penalty
        )

        # Update episode tracking counters
        if action > 0 and action_valid:
            self.ep_migrations += 1
            if migrated_vm_id:
                self.ep_unique_vms.add(migrated_vm_id)
            if target_node_id:
                self.ep_unique_destinations.add(target_node_id)
        elif action == 0:
            self.ep_no_ops += 1

        if not action_valid:
            self.ep_invalid_actions += 1

        self.ep_sla_breaches += sla_breaches
        if overloaded_nodes:
            self.ep_overloaded_steps += 1

        self.ep_reward_breakdown["fairness"] += step_fairness_reward
        self.ep_reward_breakdown["cpu_std"] += step_cpu_std_penalty
        self.ep_reward_breakdown["stability"] += step_stability_bonus
        self.ep_reward_breakdown["sla"] += step_sla_penalty
        self.ep_reward_breakdown["overload"] += step_overload_penalty
        self.ep_reward_breakdown["migration"] += step_migration_penalty
        self.ep_reward_breakdown["invalid"] += step_invalid_penalty
        self.ep_reward_breakdown["total"] += total_step_reward

        # Terminate if max steps reached
        terminated = self.current_step >= self.max_steps
        truncated = False

        obs = self.adapter.extract_features(self.cluster)
        info = {
            "step": self.current_step,
            "action": action,
            "action_executed": action_executed,
            "action_valid": action_valid,
            "jains_fairness": jains,
            "cpu_std": cpu_std,
            "sla_breaches": sla_breaches,
            "overloaded_nodes": len(overloaded_nodes),
            "action_mask": self.action_masks(),
            "reward_breakdown": {
                "fairness": step_fairness_reward,
                "cpu_std": step_cpu_std_penalty,
                "stability": step_stability_bonus,
                "sla": step_sla_penalty,
                "overload": step_overload_penalty,
                "migration": step_migration_penalty,
                "invalid": step_invalid_penalty,
                "step_total": total_step_reward,
            },
            "cumulative": {
                "migrations": self.ep_migrations,
                "no_ops": self.ep_no_ops,
                "invalid_actions": self.ep_invalid_actions,
                "sla_breaches": self.ep_sla_breaches,
                "overload_steps": self.ep_overloaded_steps,
                "unique_vms": len(self.ep_unique_vms),
                "unique_destinations": len(self.ep_unique_destinations),
                "reward_breakdown": {k: round(v, 2) for k, v in self.ep_reward_breakdown.items()},
                "scenario": self.scenario
            }
        }

        return obs, float(total_step_reward), terminated, truncated, info

    def render(self) -> str:
        if not self.cluster:
            return "No cluster initialized."
        lines = [f"--- Step {self.current_step} ---"]
        for nid, node in self.cluster.nodes.items():
            lines.append(f"  {nid}: CPU {node.cpu_percent:.1f}%, RAM {node.ram_percent:.1f}%, VMs: {node.active_vms}")
        return "\n".join(lines)
