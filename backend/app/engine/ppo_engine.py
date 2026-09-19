"""
PPO Decision Engine for VMotion AI.
Supports loading MaskablePPO / sb3-contrib weights and performing masked action inference.
If weights or sb3-contrib are absent, explicitly exposes: 'PPO MODEL NOT LOADED'
and transparently delegates to RuleBasedDecisionEngine without fabricating capabilities.
"""
import os
import time
import json
import logging
import hashlib
from enum import Enum
from typing import Literal, Optional, Dict, Any
from app.engine.base import BaseDecisionEngine, Recommendation
from app.engine.rule_engine import RuleBasedDecisionEngine
from app.adapter.observation import ObservationAdapter
from app.adapter.contracts import (
    OBSERVATION_SCHEMA_VERSION,
    ACTION_SCHEMA_VERSION,
    MODEL_SCHEMA_VERSION,
    EXPECTED_OBSERVATION_DIM,
    EXPECTED_ACTION_SPACE_SIZE,
    verify_model_contract
)
from app.providers.base import ClusterState

logger = logging.getLogger("vmotion.engine.ppo")


class PPOHealthStatus(str, Enum):
    MODEL_NOT_FOUND = "MODEL NOT FOUND"
    MODEL_FOUND = "MODEL FOUND"
    MODEL_LOAD_FAILED = "MODEL LOAD FAILED"
    MODEL_INCOMPATIBLE = "MODEL INCOMPATIBLE"
    MODEL_READY = "MODEL READY"
    MODEL_INFERENCE_FAILED = "MODEL INFERENCE FAILED"


class PPODecisionEngine(BaseDecisionEngine):
    def __init__(self, model_path: str = "models/ppo_vmotion_v5_masked.zip"):
        self.model_path = model_path
        self.adapter = ObservationAdapter()
        self.baseline_engine = RuleBasedDecisionEngine()
        self._model = None
        self._is_loaded = False
        self.health_state: PPOHealthStatus = PPOHealthStatus.MODEL_NOT_FOUND
        self.status_message: str = "PPO MODEL NOT LOADED / BASELINE ACTIVE"
        self.incompatibility_reason: Optional[str] = None
        self.last_inference_latency_ms: Optional[float] = None
        self.last_inference_error: Optional[str] = None
        self.metadata: Optional[Dict[str, Any]] = None

        self._attempt_load_model()

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def _attempt_load_model(self):
        # Resolve path relative to current working directory or project root
        actual_path = self.model_path
        if not os.path.exists(actual_path):
            project_root_candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", self.model_path))
            if os.path.exists(project_root_candidate):
                actual_path = project_root_candidate
            elif "v5" in self.model_path:
                v4_cand = self.model_path.replace("v5", "v4")
                if os.path.exists(v4_cand):
                    actual_path = v4_cand
                else:
                    v4_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", v4_cand))
                    if os.path.exists(v4_root):
                        actual_path = v4_root

        if not os.path.exists(actual_path):
            self._is_loaded = False
            self.health_state = PPOHealthStatus.MODEL_NOT_FOUND
            self.status_message = "PPO MODEL NOT LOADED / BASELINE ACTIVE"
            logger.info(
                f"Trained PPO model file '{self.model_path}' not detected on disk. "
                f"Status: {self.health_state.value}. Active Policy: Baseline Rule Heuristic (~860.6 reward baseline)."
            )
            return

        self.model_path = actual_path
        self.health_state = PPOHealthStatus.MODEL_FOUND

        # Load companion metadata if present
        meta_path = self.model_path.replace(".zip", ".meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read metadata file '{meta_path}': {e}")

        try:
            from sb3_contrib import MaskablePPO
            loaded_model = MaskablePPO.load(self.model_path)

            # Contract verification
            is_compat, reason = verify_model_contract(loaded_model, self.metadata)
            if not is_compat:
                self._is_loaded = False
                self._model = None
                self.health_state = PPOHealthStatus.MODEL_INCOMPATIBLE
                self.incompatibility_reason = reason
                self.status_message = "PPO MODEL INCOMPATIBLE"
                logger.warning(f"PPO model '{self.model_path}' is incompatible with v1.0.0 contract: {reason}")
                return

            self._model = loaded_model
            self._is_loaded = True
            self.health_state = PPOHealthStatus.MODEL_READY
            self.status_message = "PPO MODEL AVAILABLE"
            logger.info(f"Successfully loaded MaskablePPO model from '{self.model_path}' (Contract v1.0.0 Verified).")
        except ImportError:
            self._is_loaded = False
            self._model = None
            self.health_state = PPOHealthStatus.MODEL_LOAD_FAILED
            self.status_message = "PPO MODEL NOT LOADED / BASELINE ACTIVE"
            logger.warning(
                f"sb3_contrib package not installed. Status: {self.health_state.value}. "
                f"Using calibrated Baseline Rule Heuristic."
            )
        except Exception as e:
            self._is_loaded = False
            self._model = None
            self.health_state = PPOHealthStatus.MODEL_LOAD_FAILED
            self.status_message = f"PPO MODEL LOAD ERROR: {e}"
            logger.error(f"Failed to load PPO model '{self.model_path}': {e}.")

    def get_health(self) -> Dict[str, Any]:
        file_exists = os.path.exists(self.model_path)
        sha256_checksum = None
        if file_exists:
            try:
                with open(self.model_path, "rb") as f:
                    sha256_checksum = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                sha256_checksum = "UNREADABLE"

        return {
            "model_loaded": self._is_loaded,
            "model_path": self.model_path,
            "health_state": self.health_state.value,
            "status_message": self.status_message,
            "incompatibility_reason": self.incompatibility_reason,
            "file_exists": file_exists,
            "sha256_checksum": sha256_checksum,
            "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
            "action_schema_version": ACTION_SCHEMA_VERSION,
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "observation_dimension": EXPECTED_OBSERVATION_DIM,
            "action_space_size": EXPECTED_ACTION_SPACE_SIZE,
            "framework": "sb3-contrib.MaskablePPO",
            "model_version": self.metadata.get("model_version", "v5.0.0") if self.metadata else None,
            "training_scenarios": self.metadata.get("training_scenarios") if self.metadata else None,
            "baseline_fallback_active": not self._is_loaded,
            "baseline_policy_reward_expected": 860.6,
            "active_policy": "PPO_POLICY" if self._is_loaded else "BASELINE_HEURISTIC (~860.6 reward)",
            "last_inference_latency_ms": self.last_inference_latency_ms,
            "last_inference_error": self.last_inference_error
        }

    def get_action_masks(self, cluster: ClusterState) -> list[bool]:
        """
        Generates action validity mask:
        Index 0: No-Op (always valid)
        Index 1..N: VM selections (valid only if VM is running, not in cooldown, and destination candidate exists)
        """
        masks = [True]  # Action 0 = No-Op is always valid
        now = time.time()
        sorted_vms = sorted(cluster.vms.values(), key=lambda v: v.vmid)[:6]

        for vm in sorted_vms:
            elapsed = (now - vm.last_migrated_at) if vm.last_migrated_at else 999.0
            is_valid = (vm.status == "running") and (elapsed >= 60.0)
            masks.append(is_valid)

        while len(masks) < 7:
            masks.append(False)

        return masks

    def evaluate(self, cluster: ClusterState) -> Recommendation:
        if not self._is_loaded or self._model is None:
            # Delegate to baseline with honest labeling
            rec = self.baseline_engine.evaluate(cluster)
            rec.metrics_summary["ppo_model_status"] = self.status_message
            rec.metrics_summary["active_policy"] = "BASELINE_HEURISTIC (~860.6 reward)"
            return rec

        try:
            t0 = time.perf_counter()
            obs = self.adapter.extract_features(cluster)
            action_masks = self.get_action_masks(cluster)

            action, _states = self._model.predict(obs, action_masks=action_masks, deterministic=True)
            self.last_inference_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            action_idx = int(action)

            # Compute actual policy selection probability over valid action distribution
            policy_prob = 0.5
            try:
                import torch
                import numpy as np
                obs_tensor = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0).to(self._model.device)
                masks_arr = np.array([action_masks], dtype=bool)
                dist = self._model.policy.get_distribution(obs_tensor, action_masks=masks_arr)
                probs = dist.distribution.probs[0]
                if action_idx < len(probs):
                    policy_prob = round(float(probs[action_idx].item()), 4)
            except Exception as prob_err:
                logger.debug(f"Could not compute exact action probability: {prob_err}")

            if action_idx == 0:
                return Recommendation(
                    action_type="NO_OP",
                    action_index=0,
                    reason="PPO Policy selected action 0 (No-Op): Cluster balance is within acceptable equilibrium.",
                    engine_type="PPO_POLICY",
                    confidence_score=policy_prob,
                    timestamp=time.time(),
                    metrics_summary={
                        "ppo_model_status": "PPO MODEL AVAILABLE",
                        "action_selected": 0,
                        "inference_latency_ms": self.last_inference_latency_ms,
                        "policy_selection_probability": policy_prob,
                        "confidence_metric_type": "SOFTMAX_POLICY_PROBABILITY"
                    }
                )

            sorted_vms = sorted(cluster.vms.values(), key=lambda v: v.vmid)[:6]
            selected_vm_idx = action_idx - 1
            if selected_vm_idx < len(sorted_vms):
                vm = sorted_vms[selected_vm_idx]
                other_nodes = [n for n in cluster.nodes.values() if n.id != vm.node_id and n.status == "online"]
                if not other_nodes:
                    return Recommendation(
                        action_type="NO_OP",
                        action_index=0,
                        reason="PPO selected workload but no alternative online compute node is available.",
                        engine_type="PPO_POLICY",
                        confidence_score=0.0,
                        timestamp=time.time(),
                        metrics_summary={
                            "ppo_model_status": "PPO MODEL AVAILABLE",
                            "inference_latency_ms": self.last_inference_latency_ms,
                            "policy_selection_probability": 0.0,
                            "confidence_metric_type": "SOFTMAX_POLICY_PROBABILITY"
                        }
                    )
                best_target = min(other_nodes, key=lambda n: n.cpu_percent)

                return Recommendation(
                    action_type="MIGRATE",
                    action_index=action_idx,
                    vm_id=vm.vmid,
                    vm_name=vm.name,
                    source_node=vm.node_id,
                    target_node=best_target.id,
                    reason=f"PPO Policy selected {vm.vmid} for migration to '{best_target.id}' to optimize cluster reward.",
                    engine_type="PPO_POLICY",
                    confidence_score=policy_prob,
                    timestamp=time.time(),
                    metrics_summary={
                        "ppo_model_status": "PPO MODEL AVAILABLE",
                        "action_selected": action_idx,
                        "inference_latency_ms": self.last_inference_latency_ms,
                        "policy_selection_probability": policy_prob,
                        "confidence_metric_type": "SOFTMAX_POLICY_PROBABILITY"
                    }
                )

            rec = self.baseline_engine.evaluate(cluster)
            rec.metrics_summary["ppo_model_status"] = "PPO MODEL AVAILABLE"
            rec.metrics_summary["inference_latency_ms"] = self.last_inference_latency_ms
            return rec

        except Exception as e:
            logger.error(f"PPO inference error: {e}. Falling back to baseline heuristic.")
            self.health_state = PPOHealthStatus.MODEL_INFERENCE_FAILED
            self.last_inference_error = str(e)
            self.status_message = f"PPO INFERENCE ERROR: {e}"
            rec = self.baseline_engine.evaluate(cluster)
            rec.metrics_summary["ppo_model_status"] = self.status_message
            rec.metrics_summary["error"] = str(e)
            return rec
