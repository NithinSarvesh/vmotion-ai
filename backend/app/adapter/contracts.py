"""
Observation & Action Contract Specifications and Versioning for VMotion AI.
Guarantees compatibility between the hypervisor telemetry observation adapter,
the reinforcement learning environment, and the trained MaskablePPO policy checkpoint.
"""
from typing import Dict, Any, Tuple, Optional
import numpy as np

OBSERVATION_SCHEMA_VERSION = "v1.0.0"
ACTION_SCHEMA_VERSION = "v1.0.0"
MODEL_SCHEMA_VERSION = "v1.0.0"

EXPECTED_OBSERVATION_DIM = 103
EXPECTED_ACTION_SPACE_SIZE = 7

# Contract slot definition
NODE_SLOT_COUNT = 3
FEATURES_PER_NODE = 8
VM_SLOT_COUNT = 6
FEATURES_PER_VM = 10
GLOBAL_FEATURE_COUNT = 19

ACTION_SEMANTICS: Dict[int, str] = {
    0: "NO_OP: Maintain current workload placement",
    1: "MIGRATE_VM_SLOT_0: Rebalance workload at slot 0 (alphanumeric order)",
    2: "MIGRATE_VM_SLOT_1: Rebalance workload at slot 1 (alphanumeric order)",
    3: "MIGRATE_VM_SLOT_2: Rebalance workload at slot 2 (alphanumeric order)",
    4: "MIGRATE_VM_SLOT_3: Rebalance workload at slot 3 (alphanumeric order)",
    5: "MIGRATE_VM_SLOT_4: Rebalance workload at slot 4 (alphanumeric order)",
    6: "MIGRATE_VM_SLOT_5: Rebalance workload at slot 5 (alphanumeric order)",
}


def verify_model_contract(model: Any, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Verifies that a loaded Stable-Baselines3 / MaskablePPO model satisfies the
    exact v1.0.0 103-dim observation and Discrete(7) action space contract.
    """
    if model is None:
        return False, "Model object is None."

    # Check observation space
    obs_space = getattr(model, "observation_space", None)
    if obs_space is None:
        return False, "Model has no observation_space attribute."

    obs_shape = getattr(obs_space, "shape", None)
    if obs_shape != (EXPECTED_OBSERVATION_DIM,):
        return False, (
            f"Observation dimension mismatch: model expects {obs_shape}, "
            f"contract requires ({EXPECTED_OBSERVATION_DIM},)."
        )

    # Check action space
    act_space = getattr(model, "action_space", None)
    if act_space is None:
        return False, "Model has no action_space attribute."

    act_n = getattr(act_space, "n", None)
    if act_n != EXPECTED_ACTION_SPACE_SIZE:
        return False, (
            f"Action space mismatch: model expects Discrete({act_n}), "
            f"contract requires Discrete({EXPECTED_ACTION_SPACE_SIZE})."
        )

    # Check companion metadata if provided
    if metadata:
        obs_ver = metadata.get("observation_schema_version")
        if obs_ver and obs_ver != OBSERVATION_SCHEMA_VERSION:
            return False, (
                f"Observation schema version mismatch: checkpoint is '{obs_ver}', "
                f"runtime expects '{OBSERVATION_SCHEMA_VERSION}'."
            )
        act_ver = metadata.get("action_schema_version")
        if act_ver and act_ver != ACTION_SCHEMA_VERSION:
            return False, (
                f"Action schema version mismatch: checkpoint is '{act_ver}', "
                f"runtime expects '{ACTION_SCHEMA_VERSION}'."
            )

    return True, "Model satisfies all contract specifications."
