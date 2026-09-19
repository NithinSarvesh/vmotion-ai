"""
Automated unit tests for VMotion AI 103-Feature Observation Adapter.
"""
import pytest
import numpy as np
from app.providers.simulation import SimulationProvider
from app.adapter.observation import ObservationAdapter


@pytest.mark.asyncio
async def test_observation_dimensions_and_bounds():
    provider = SimulationProvider()
    cluster = await provider.get_cluster_state()
    adapter = ObservationAdapter()

    obs = adapter.extract_features(cluster)
    
    # Verify exact 103 dimensions required by the PPO specification
    assert isinstance(obs, np.ndarray)
    assert obs.shape == (103,), f"Expected 103 features, got shape {obs.shape}"

    # Verify normalization bounds
    assert not np.isnan(obs).any(), "Observation vector contains NaN"
    assert not np.isinf(obs).any(), "Observation vector contains Inf"
    assert (obs >= -1.0).all(), "Observation features violated lower bound (-1.0)"
    assert (obs <= 1.0).all(), "Observation features violated upper bound (1.0)"
