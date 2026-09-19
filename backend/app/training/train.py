"""
Reproducible Training Script for MaskablePPO in VMotion AI.
Uses sb3_contrib.MaskablePPO with ActionMasker wrapper on VMotionEnv.
"""
import os
import argparse
import time
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.evaluation import evaluate_policy
from sb3_contrib.common.wrappers import ActionMasker
from typing import Optional, Dict, Any, List
from app.training.environment import VMotionEnv
from app.training.evaluate import run_benchmark


def mask_fn(env: VMotionEnv) -> np.ndarray:
    return env.action_masks()


def train(
    timesteps: int = 50000,
    seed: int = 42,
    output_path: str = "models/ppo_vmotion_v5_masked.zip",
    log_dir: str = "models/logs",
    learning_rate: float = 3e-4,
    batch_size: int = 64,
    gamma: float = 0.99,
    ent_coef: float = 0.03,
    scenario_distribution: Optional[dict] = None,
    use_curriculum: bool = False
):
    print("=" * 70)
    print("VMOTION AI — MASKABLE PPO RL TRAINING PIPELINE (V5)")
    print(f"Target Timesteps: {timesteps}")
    print(f"Random Seed:      {seed}")
    print(f"Output File:      {output_path}")
    print(f"Log Directory:    {log_dir}")
    print(f"Entropy Coef:     {ent_coef}")
    print(f"Curriculum:       {use_curriculum}")
    print("=" * 70)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    default_dist = {
        "NORMAL": 0.25,
        "CPU_HOTSPOT": 0.25,
        "RAM_HOTSPOT": 0.25,
        "MIXED_OVERLOAD": 0.25
    }
    active_dist = scenario_distribution or default_dist

    curriculum_cfg = None
    if use_curriculum:
        s1 = int(timesteps * 0.2)
        s2 = int(timesteps * 0.5)
        curriculum_cfg = {
            "enabled": True,
            "stages": [
                {"until_step": s1, "distribution": {"NORMAL": 0.50, "CPU_HOTSPOT": 0.25, "RAM_HOTSPOT": 0.25}},
                {"until_step": s2, "distribution": {"NORMAL": 0.30, "CPU_HOTSPOT": 0.35, "RAM_HOTSPOT": 0.35}},
                {"until_step": timesteps * 2, "distribution": active_dist}
            ]
        }
        print(f"Curriculum enabled: Stage 1 (0-{s1} steps), Stage 2 ({s1}-{s2} steps), Stage 3 ({s2}+ steps)")
    else:
        print(f"Scenario distribution: {active_dist}")

    # Instantiate environment wrapped with ActionMasker
    raw_env_ref = None
    def make_env():
        nonlocal raw_env_ref
        raw_env_ref = VMotionEnv(
            max_steps=100,
            scenario_distribution=active_dist,
            curriculum_config=curriculum_cfg,
            seed=seed
        )
        return ActionMasker(raw_env_ref, mask_fn)

    env = make_env()

    # Check if tensorboard is available
    has_tb = False
    try:
        import tensorboard
        has_tb = True
    except ImportError:
        pass

    # Initialize MaskablePPO
    model = MaskablePPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=2048,
        batch_size=batch_size,
        n_epochs=10,
        gamma=gamma,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=ent_coef,
        verbose=1,
        seed=seed,
        tensorboard_log=log_dir if has_tb else None
    )

    print("\nStarting PPO optimization...")
    start_time = time.time()
    model.learn(total_timesteps=timesteps)
    elapsed = time.time() - start_time
    print(f"\nTraining completed in {elapsed:.1f}s ({timesteps / max(1.0, elapsed):.1f} steps/s).")

    # Save trained model weights
    model.save(output_path)
    print(f"Model saved successfully to: {output_path}")

    # Scenario distribution summary from training
    scenario_summary = raw_env_ref.get_training_scenario_summary() if raw_env_ref else {}
    print("\nTraining Scenario Execution Summary:")
    for sc, s_data in scenario_summary.get("scenarios", {}).items():
        print(f"  - {sc:<18}: {s_data['episodes']} episodes ({s_data['percentage_episodes']}%), {s_data['steps']} steps ({s_data['percentage_steps']}%)")

    # Evaluate trained model
    eval_env = make_env()
    mean_r, std_r = evaluate_policy(model, eval_env, n_eval_episodes=10)
    print(f"\nEvaluation over 10 episodes: Mean Reward = {mean_r:.2f} +/- {std_r:.2f}")

    # Calculate SHA-256 checksum of saved artifact
    import hashlib
    import json
    from app.adapter.contracts import (
        OBSERVATION_SCHEMA_VERSION,
        ACTION_SCHEMA_VERSION,
        MODEL_SCHEMA_VERSION,
        EXPECTED_OBSERVATION_DIM,
        EXPECTED_ACTION_SPACE_SIZE
    )

    with open(output_path, "rb") as f:
        sha256_val = hashlib.sha256(f.read()).hexdigest()

    meta_path = output_path.replace(".zip", ".meta.json")
    metadata = {
        "model_name": os.path.basename(output_path),
        "model_version": "v5.0.0",
        "created_at": time.time(),
        "seed": seed,
        "environment_version": "v1.0.0",
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "action_schema_version": ACTION_SCHEMA_VERSION,
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "observation_dim": EXPECTED_OBSERVATION_DIM,
        "action_space_size": EXPECTED_ACTION_SPACE_SIZE,
        "hyperparameters": {
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "gamma": gamma,
            "n_steps": 2048,
            "n_epochs": 10,
            "gae_lambda": 0.95,
            "clip_range": 0.2,
            "ent_coef": ent_coef
        },
        "total_timesteps": timesteps,
        "training_scenarios": scenario_summary,
        "curriculum_enabled": use_curriculum,
        "evaluation": {
            "episodes": 10,
            "mean_reward": round(float(mean_r), 2),
            "std_reward": round(float(std_r), 2)
        },
        "sha256_checksum": sha256_val
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Companion metadata saved: {meta_path}")

    # Run comparative benchmark
    print("\nRunning Comparative Multi-Policy Benchmark:")
    run_benchmark(episodes=5, model_path=output_path)

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train VMotion AI MaskablePPO Policy")
    parser.add_argument("--timesteps", type=int, default=50000, help="Total environment timesteps to train")
    parser.add_argument("--seed", type=int, default=42, help="Reproducible PRNG seed")
    parser.add_argument("--output", type=str, default="models/ppo_vmotion_v5_masked.zip", help="Destination model path")
    parser.add_argument("--log-dir", type=str, default="models/logs", help="TensorBoard log directory")
    parser.add_argument("--ent-coef", type=float, default=0.03, help="Entropy coefficient")
    parser.add_argument("--curriculum", action="store_true", help="Enable 3-stage curriculum training")
    args = parser.parse_args()

    train(
        timesteps=args.timesteps,
        seed=args.seed,
        output_path=args.output,
        log_dir=args.log_dir,
        ent_coef=args.ent_coef,
        use_curriculum=args.curriculum
    )
