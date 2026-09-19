"""
Rule-Based Baseline Decision Engine.
Implements the reference baseline algorithm that achieved ~860.6 reward in earlier research.
Evaluates cluster imbalance, SLA penalties, resource contention, and destination headroom.
"""
import time
from app.engine.base import BaseDecisionEngine, Recommendation
from app.providers.base import ClusterState


class RuleBasedDecisionEngine(BaseDecisionEngine):
    def __init__(self, cpu_imbalance_threshold: float = 20.0, node_overload_threshold: float = 70.0):
        self.cpu_imbalance_threshold = cpu_imbalance_threshold
        self.node_overload_threshold = node_overload_threshold

    def evaluate(self, cluster: ClusterState) -> Recommendation:
        now = time.time()
        online_nodes = [n for n in cluster.nodes.values() if n.status == "online"]
        if len(online_nodes) < 2:
            return Recommendation(
                action_type="NO_OP",
                reason="Insufficient online nodes in cluster to perform migration.",
                engine_type="BASELINE_RULE",
                confidence_score=0.0,
                timestamp=now
            )

        # Sort nodes by CPU utilization
        nodes_by_cpu = sorted(online_nodes, key=lambda n: n.cpu_percent, reverse=True)
        hottest_node = nodes_by_cpu[0]
        coldest_node = nodes_by_cpu[-1]

        cpu_spread = hottest_node.cpu_percent - coldest_node.cpu_percent

        # If hottest node is not overloaded and cluster is well-balanced, No-Op
        if hottest_node.cpu_percent < self.node_overload_threshold and cpu_spread < self.cpu_imbalance_threshold:
            return Recommendation(
                action_type="NO_OP",
                action_index=0,
                reason=f"Cluster load balanced. Max CPU {hottest_node.cpu_percent:.1f}%, spread {cpu_spread:.1f}%.",
                engine_type="BASELINE_RULE",
                confidence_score=0.92,
                timestamp=now,
                metrics_summary={
                    "hottest_node": hottest_node.id,
                    "coldest_node": coldest_node.id,
                    "cpu_spread": round(cpu_spread, 1)
                }
            )

        # Find candidates on the hottest node
        candidate_vms = [
            v for v in cluster.vms.values()
            if v.node_id == hottest_node.id
            and v.status == "running"
            and (now - (v.last_migrated_at or 0.0)) > 60.0  # respect cooldown
        ]

        if not candidate_vms:
            return Recommendation(
                action_type="NO_OP",
                action_index=0,
                reason=f"Hottest node '{hottest_node.id}' has load ({hottest_node.cpu_percent:.1f}%), but all candidate VMs are cooling down or migrating.",
                engine_type="BASELINE_RULE",
                confidence_score=0.75,
                timestamp=now
            )

        # Sort candidate VMs: prefer standard/batch SLA over critical SLA to reduce risk
        # Also choose VM that relieves significant CPU without overwhelming the target node
        free_ram_target = coldest_node.ram_total_mb - coldest_node.ram_used_mb
        viable_vms = [v for v in candidate_vms if v.ram_allocated_mb <= free_ram_target]

        if not viable_vms:
            return Recommendation(
                action_type="NO_OP",
                action_index=0,
                reason=f"No candidate VM on '{hottest_node.id}' fits into available memory on target '{coldest_node.id}' ({free_ram_target:.0f}MB free).",
                engine_type="BASELINE_RULE",
                confidence_score=0.80,
                timestamp=now
            )

        # Score candidates: higher CPU relief, lower SLA risk
        sla_risk = {"critical": 3.0, "high": 2.0, "standard": 1.0, "batch": 0.5}
        best_vm = min(viable_vms, key=lambda v: (sla_risk.get(v.sla_priority, 1.0), -v.cpu_percent))

        # Calculate projected balance improvement
        projected_source_cpu = hottest_node.cpu_percent - (best_vm.cpu_cores / hottest_node.cpu_cores * best_vm.cpu_percent)
        projected_target_cpu = coldest_node.cpu_percent + (best_vm.cpu_cores / coldest_node.cpu_cores * best_vm.cpu_percent)
        projected_spread = abs(projected_source_cpu - projected_target_cpu)
        improvement = max(0.0, cpu_spread - projected_spread)

        # Honest confidence calculation based on load delta and SLA safety
        confidence = min(0.96, max(0.65, 0.70 + (improvement / 100.0) * 0.3))

        sorted_all_vms = sorted(cluster.vms.keys())
        action_idx = sorted_all_vms.index(best_vm.vmid) + 1 if best_vm.vmid in sorted_all_vms else 1

        return Recommendation(
            action_type="MIGRATE",
            action_index=action_idx,
            vm_id=best_vm.vmid,
            vm_name=best_vm.name,
            source_node=hottest_node.id,
            target_node=coldest_node.id,
            reason=f"High compute pressure on '{hottest_node.id}' ({hottest_node.cpu_percent:.1f}%). Rebalancing {best_vm.vmid} ({best_vm.name}) to '{coldest_node.id}' ({coldest_node.cpu_percent:.1f}%).",
            engine_type="BASELINE_RULE",
            confidence_score=round(confidence, 2),
            expected_load_balance_improvement=round(improvement, 2),
            timestamp=now,
            metrics_summary={
                "source_cpu_current": round(hottest_node.cpu_percent, 1),
                "source_cpu_projected": round(max(0.0, projected_source_cpu), 1),
                "target_cpu_current": round(coldest_node.cpu_percent, 1),
                "target_cpu_projected": round(projected_target_cpu, 1),
                "target_ram_available_mb": round(free_ram_target, 0),
                "vm_allocated_ram_mb": round(best_vm.ram_allocated_mb, 0),
                "sla_tier": best_vm.sla_priority,
                "confidence_metric_type": "HEURISTIC_LOAD_GRADIENT_ESTIMATE"
            }
        )
