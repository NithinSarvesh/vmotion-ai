"""
Validation Module for VMotion AI Reinforcement Learning Model Checkpoints.
Validates model weights, contract compliance (v1.0.0), companion metadata, and inference execution.
"""
import os
import sys
import json
import hashlib
import argparse
from typing import Dict, Any, Tuple

from app.adapter.contracts import (
    OBSERVATION_SCHEMA_VERSION,
    ACTION_SCHEMA_VERSION,
    MODEL_SCHEMA_VERSION,
    EXPECTED_OBSERVATION_DIM,
    EXPECTED_ACTION_SPACE_SIZE,
    verify_model_contract
)
from app.training.environment import VMotionEnv


def validate_checkpoint(model_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validates a PPO model checkpoint against contract v1.0.0 specifications.
    Returns (is_valid, validation_report).
    """
    report: Dict[str, Any] = {
        "model_path": model_path,
        "file_exists": False,
        "sha256": None,
        "metadata_found": False,
        "metadata": None,
        "load_successful": False,
        "contract_verified": False,
        "inference_test_passed": False,
        "errors": []
    }

    if not os.path.exists(model_path):
        report["errors"].append(f"Model file '{model_path}' does not exist.")
        return False, report

    report["file_exists"] = True

    # Calculate SHA-256
    try:
        with open(model_path, "rb") as f:
            report["sha256"] = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        report["errors"].append(f"Failed to read file for checksum: {e}")
        return False, report

    # Check companion metadata
    meta_path = model_path.replace(".zip", ".meta.json")
    if os.path.exists(meta_path):
        report["metadata_found"] = True
        try:
            with open(meta_path, "r") as f:
                report["metadata"] = json.load(f)
        except Exception as e:
            report["errors"].append(f"Failed to parse metadata JSON: {e}")

    # Load model
    try:
        from sb3_contrib import MaskablePPO
        model = MaskablePPO.load(model_path)
        report["load_successful"] = True
    except Exception as e:
        report["errors"].append(f"MaskablePPO failed to load model: {e}")
        return False, report

    # Verify contract
    is_compat, reason = verify_model_contract(model, report["metadata"])
    if not is_compat:
        report["errors"].append(f"Contract incompatibility: {reason}")
        return False, report

    report["contract_verified"] = True

    # Test inference step on fresh environment state
    try:
        env = VMotionEnv(max_steps=10, seed=42)
        obs, info = env.reset(seed=42)
        masks = info["action_mask"]

        action, _ = model.predict(obs, action_masks=masks, deterministic=True)
        action_idx = int(action)
        if not (0 <= action_idx < EXPECTED_ACTION_SPACE_SIZE):
            report["errors"].append(f"Inference returned out-of-range action: {action_idx}")
            return False, report

        report["inference_test_passed"] = True
        report["sample_action_selected"] = action_idx
    except Exception as e:
        report["errors"].append(f"Inference execution test failed: {e}")
        return False, report

    return True, report


def main():
    parser = argparse.ArgumentParser(description="Validate VMotion AI PPO Model Checkpoint")
    parser.add_argument("--model-path", type=str, default="models/ppo_vmotion_v4_masked.zip", help="Path to .zip model file")
    args = parser.parse_args()

    print("=" * 70)
    print(f"VMOTION AI — MODEL CHECKPOINT VALIDATION: {args.model_path}")
    print("=" * 70)

    is_valid, report = validate_checkpoint(args.model_path)

    print(f"\nFile Exists:        {report['file_exists']}")
    print(f"SHA-256 Checksum:   {report['sha256']}")
    print(f"Companion Metadata: {report['metadata_found']}")
    print(f"Load Status:        {'SUCCESS' if report['load_successful'] else 'FAILED'}")
    print(f"Contract Verified:  {'COMPATIBLE (v1.0.0)' if report['contract_verified'] else 'INCOMPATIBLE'}")
    print(f"Inference Test:     {'PASSED' if report['inference_test_passed'] else 'FAILED'}")

    if report["errors"]:
        print("\nErrors Detected:")
        for err in report["errors"]:
            print(f"  - {err}")

    print("\n" + "=" * 70)
    if is_valid:
        print("RESULT: MODEL IS VERIFIED AND READY FOR CONTROL PLANE INFERENCE")
        sys.exit(0)
    else:
        print("RESULT: MODEL VALIDATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
