"""
Unit tests for VMotion AI Gymnasium RL Environment and Evaluation.
"""
import pytest
import numpy as np
from app.training.environment import VMotionEnv
from app.training.evaluate import evaluate_baseline_policy, evaluate_random_policy


def test_environment_spaces():
    env = VMotionEnv(max_steps=50, seed=42)
    obs, info = env.reset(seed=42)

    assert obs.shape == (103,)
    assert obs.dtype == np.float32
    assert not np.isnan(obs).any()
    assert not np.isinf(obs).any()
    assert env.action_space.n == 7

    # Check action masks
    masks = env.action_masks()
    assert isinstance(masks, np.ndarray)
    assert masks.shape == (7,)
    assert masks.dtype == bool
    assert masks[0] is True or masks[0] == 1  # Action 0 is always valid


def test_environment_step_progression():
    env = VMotionEnv(max_steps=10, seed=123)
    obs, info = env.reset(seed=123)

    # Step No-Op
    next_obs, reward, terminated, truncated, info = env.step(0)
    assert next_obs.shape == (103,)
    assert isinstance(reward, float)
    assert not terminated
    assert info["action"] == 0
    assert "jains_fairness" in info
    assert "cpu_std" in info


def test_environment_invalid_action_penalty():
    env = VMotionEnv(max_steps=10, seed=999)
    env.reset(seed=999)

    # Pick an action that is masked out (if any) or forced invalid
    masks = env.action_masks()
    invalid_actions = [i for i, valid in enumerate(masks) if not valid]
    if invalid_actions:
        bad_action = invalid_actions[0]
        _, reward, _, _, info = env.step(bad_action)
        assert not info["action_valid"]
        assert reward < 0.0


def test_baseline_evaluation_runs():
    env = VMotionEnv(max_steps=20, seed=42)
    res = evaluate_baseline_policy(env, episodes=2, seed=42)
    assert res["policy"] == "Baseline Heuristic"
    assert res["episodes"] == 2
    assert isinstance(res["mean_reward"], float)
    assert "mean_final_jains" in res


def test_random_evaluation_runs():
    env = VMotionEnv(max_steps=20, seed=42)
    res = evaluate_random_policy(env, episodes=2, seed=42)
    assert res["policy"] == "Random Valid Masked Policy"
    assert res["episodes"] == 2
    assert isinstance(res["mean_reward"], float)


def test_severe_hotspot_action_mask_allows_migrations():
    """
    Requirement Phase 5: Deliberately creates a severe hotspot where at least
    one migration action MUST be valid.
    Asserts that action mask contains [True, True/..., ...] rather than
    [True, False, False, False, False, False, False].
    """
    env = VMotionEnv(max_steps=50, seed=42)
    obs, info = env.reset(seed=42, options={"scenario": "CPU_HOTSPOT"})
    masks = info["action_mask"]

    assert bool(masks[0]) is True, "Action 0 (No-Op) must always be valid"
    assert any(masks[1:]), "At least one migration action must be valid during a severe hotspot"
    assert not np.array_equal(masks, [True, False, False, False, False, False, False]), (
        "Action mask must NOT be strictly [True, False, False, False, False, False, False] in a hotspot state"
    )

    # Verify that the heaviest VM on the overloaded host (vm-101) is valid to migrate
    sorted_vms = sorted(env.cluster.vms.values(), key=lambda v: v.vmid)[:6]
    vm_101_idx = [i for i, v in enumerate(sorted_vms) if v.vmid == "vm-101"][0]
    action_for_vm_101 = vm_101_idx + 1
    assert bool(masks[action_for_vm_101]) is True, f"Action {action_for_vm_101} for vm-101 must be valid in action mask"

