"""
Automated unit tests for rigorous mathematical verification of the 103-Dimensional Observation Space.
Adheres strictly to docs/OBSERVATION_SPEC_103.md.
"""
import pytest
import numpy as np
import time
from app.providers.simulation import SimulationProvider
from app.adapter.observation import ObservationAdapter
from app.providers.base import ClusterState, NodeTelemetry, VMTelemetry


@pytest.mark.asyncio
async def test_observation_vector_exact_length_and_types():
    provider = SimulationProvider()
    cluster = await provider.collect_telemetry()
    adapter = ObservationAdapter()

    obs = adapter.extract_features(cluster)
    assert isinstance(obs, np.ndarray)
    assert obs.dtype == np.float32
    assert obs.shape == (103,), f"Expected exactly 103 dimensions, got {obs.shape}"

    # Strict NaN & Inf checks
    assert not np.isnan(obs).any(), "Observation vector contains NaN!"
    assert not np.isinf(obs).any(), "Observation vector contains Inf!"


@pytest.mark.asyncio
async def test_observation_feature_bounds():
    provider = SimulationProvider()
    cluster = await provider.collect_telemetry()
    adapter = ObservationAdapter()

    obs = adapter.extract_features(cluster)

    # Node Features: Indices 0..23 (all in [0.0, 1.0])
    for idx in range(24):
        val = obs[idx]
        assert 0.0 <= val <= 1.0, f"Node feature at index {idx} out of bounds [0.0, 1.0]: {val}"

    # VM Features: Indices 24..83 (all in [0.0, 1.0] except node index in [-1.0, 1.0])
    for v_idx in range(6):
        base = 24 + 10 * v_idx
        # First 9 features in [0.0, 1.0]
        for offset in range(9):
            val = obs[base + offset]
            assert 0.0 <= val <= 1.0, f"VM {v_idx} feature at index {base + offset} out of bounds: {val}"
        # Node index in [-1.0, 1.0]
        node_idx_val = obs[base + 9]
        assert -1.0 <= node_idx_val <= 1.0, f"VM {v_idx} node index out of bounds: {node_idx_val}"

    # Global Features: Indices 84..102 (all in [0.0, 1.0])
    for idx in range(84, 103):
        val = obs[idx]
        assert 0.0 <= val <= 1.0, f"Global feature at index {idx} out of bounds [0.0, 1.0]: {val}"


@pytest.mark.asyncio
async def test_observation_feature_perturbation_sensitivity():
    provider = SimulationProvider()
    cluster = await provider.collect_telemetry()
    adapter = ObservationAdapter()

    obs1 = adapter.extract_features(cluster)

    # Perturb node-01 CPU
    cluster.nodes["node-01"].cpu_percent = 95.0
    obs2 = adapter.extract_features(cluster)

    # Index 0 is node-01 CPU util: should now be 0.95
    assert round(float(obs2[0]), 2) == 0.95
    assert obs2[0] != obs1[0]

    # Perturb first VM (vm-101) CPU
    vms_sorted = sorted(cluster.vms.values(), key=lambda v: v.vmid)
    first_vm = vms_sorted[0]
    first_vm.cpu_percent = 50.0
    obs3 = adapter.extract_features(cluster)

    # Index 24 is first VM's CPU util: should now be 0.50
    assert round(float(obs3[24]), 2) == 0.50


@pytest.mark.asyncio
async def test_observation_missing_nodes_and_vms_safe_defaults():
    # Construct an empty cluster
    empty_cluster = ClusterState(
        is_live=False,
        connected=True,
        provider_name="simulation",
        timestamp=time.time(),
        nodes={},
        vms={}
    )
    adapter = ObservationAdapter()
    obs = adapter.extract_features(empty_cluster)

    assert obs.shape == (103,)
    assert not np.isnan(obs).any()
    assert not np.isinf(obs).any()
    # Missing nodes should default to 0.0
    assert (obs[:24] == 0.0).all()


@pytest.mark.asyncio
async def test_observation_variable_cluster_sizes():
    provider = SimulationProvider()
    cluster = await provider.collect_telemetry()
    adapter = ObservationAdapter()

    # 2-node cluster test
    cluster_2node = ClusterState(
        is_live=False,
        connected=True,
        provider_name="simulation",
        timestamp=time.time(),
        nodes={k: v for k, v in list(cluster.nodes.items())[:2]},
        vms=cluster.vms
    )
    obs_2 = adapter.extract_features(cluster_2node)
    assert obs_2.shape == (103,)
    assert not np.isnan(obs_2).any()
    assert not np.isinf(obs_2).any()
    # Node slot 2 (indices 16..23) must be 0.0
    assert (obs_2[16:24] == 0.0).all()

    # 4-node cluster test
    node_copy = cluster.nodes["node-01"].model_copy()
    node_copy.id = "node-04"
    cluster_4node = ClusterState(
        is_live=False,
        connected=True,
        provider_name="simulation",
        timestamp=time.time(),
        nodes={**cluster.nodes, "node-04": node_copy},
        vms=cluster.vms
    )
    obs_4 = adapter.extract_features(cluster_4node)
    assert obs_4.shape == (103,)
    assert not np.isnan(obs_4).any()


def test_observation_spec_json_alignment():
    import json
    import os
    spec_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "OBSERVATION_SPEC_103.json")
    assert os.path.exists(spec_path), f"Spec file not found at {spec_path}"
    with open(spec_path, "r") as f:
        spec = json.load(f)
    assert spec["total_dimensions"] == 103
    assert len(spec["features"]) == 103
    for i, feat in enumerate(spec["features"]):
        assert feat["index"] == i, f"Feature index mismatch at {i}"

