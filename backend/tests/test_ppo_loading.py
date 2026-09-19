"""
Unit tests for PPO Decision Engine loading, action masking, and baseline fallback.
"""
import os
import tempfile
import pytest
import numpy as np
from app.engine.ppo_engine import PPODecisionEngine
from app.providers.simulation import SimulationProvider
from app.training.environment import VMotionEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


@pytest.mark.asyncio
async def test_ppo_engine_unloaded_baseline_fallback():
    # Use a non-existent path
    engine = PPODecisionEngine(model_path="models/nonexistent_model.zip")
    assert not engine._is_loaded
    assert "BASELINE ACTIVE" in engine.status_message
    
    health = engine.get_health()
    assert health["model_loaded"] is False
    assert health["baseline_fallback_active"] is True
    assert health["file_exists"] is False
    assert health["sha256_checksum"] is None

    provider = SimulationProvider()
    cluster = await provider.get_cluster_state()
    rec = engine.evaluate(cluster)
    assert rec.engine_type == "BASELINE_RULE"
    assert "PPO MODEL NOT LOADED" in rec.metrics_summary["ppo_model_status"]
    assert rec.metrics_summary["ppo_model_status"] == "PPO MODEL NOT LOADED / BASELINE ACTIVE"


@pytest.mark.asyncio
async def test_ppo_action_masks():
    engine = PPODecisionEngine(model_path="models/nonexistent_model.zip")
    provider = SimulationProvider()
    cluster = await provider.get_cluster_state()

    masks = engine.get_action_masks(cluster)
    assert len(masks) == 7
    assert masks[0] is True  # No-op always valid
    assert all(isinstance(m, (bool, np.bool_)) for m in masks)


def test_ppo_engine_load_and_predict_with_valid_model():
    # Train a minimal 64-step model to a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "test_ppo.zip")
        
        raw_env = VMotionEnv(max_steps=20, seed=42)
        env = ActionMasker(raw_env, lambda e: e.action_masks())
        
        model = MaskablePPO(
            "MlpPolicy",
            env,
            n_steps=64,
            batch_size=32,
            n_epochs=1,
            seed=42,
            verbose=0
        )
        model.learn(total_timesteps=64)
        model.save(model_path)

        # Now instantiate PPODecisionEngine pointing to this model
        loaded_engine = PPODecisionEngine(model_path=model_path)
        assert loaded_engine._is_loaded is True
        assert loaded_engine.status_message == "PPO MODEL AVAILABLE"

        health = loaded_engine.get_health()
        assert health["model_loaded"] is True
        assert health["file_exists"] is True
        assert health["sha256_checksum"] is not None
        assert len(health["sha256_checksum"]) == 64
        assert health["baseline_fallback_active"] is False

        # Run inference on simulated cluster
        cluster = raw_env.cluster
        rec = loaded_engine.evaluate(cluster)
        assert rec.action_type in ("NO_OP", "MIGRATE")
        assert rec.engine_type == "PPO_POLICY"
        assert rec.confidence_score > 0.0
