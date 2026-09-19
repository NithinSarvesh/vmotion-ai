"""
Automated integration tests for VMotion AI REST API routes.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["app"] == "VMotion AI"
    assert "provider" in data


def test_api_cluster_state():
    response = client.get("/api/cluster/state")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "vms" in data
    assert len(data["nodes"]) >= 3
    assert len(data["vms"]) >= 6


def test_api_ai_recommendation():
    response = client.get("/api/ai/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert "recommendation" in data
    rec = data["recommendation"]
    assert rec["action_type"] in ("MIGRATE", "NO_OP")
    assert "engine_type" in rec


def test_api_safety_check_endpoint():
    response = client.get("/api/safety/check?vm_id=vm-101&target_node=node-02")
    assert response.status_code == 200
    data = response.json()
    assert "passed" in data
    assert "blocked" in data
    assert "results" in data
    assert len(data["results"]) == 8


def test_api_observation_features_endpoint():
    response = client.get("/api/observation/features")
    assert response.status_code == 200
    data = response.json()
    assert data["dimension"] == 103
    assert len(data["features"]) == 103


def test_api_audit_logs_endpoint():
    response = client.get("/api/audit/logs?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_api_provider_mode_switch():
    # Test switching to simulation
    res = client.post("/api/cluster/mode", json={"provider_type": "simulation"})
    assert res.status_code == 200
    assert res.json()["provider"] == "simulation"

    # Test invalid provider
    res_bad = client.post("/api/cluster/mode", json={"provider_type": "invalid_provider"})
    assert res_bad.status_code == 422  # Pydantic validation error


def test_api_settings_endpoint():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["enable_human_approval"] is True
    assert data["enable_autonomous_mode"] is False


def test_api_cluster_config_get_masks_secrets():
    res = client.get("/api/cluster/config")
    assert res.status_code == 200
    data = res.json()
    assert "proxmox" in data
    assert "libvirt" in data
    assert "token_secret" not in data["proxmox"]
    assert "token_secret_configured" in data["proxmox"]


def test_api_cluster_config_post_update():
    payload = {
        "proxmox_endpoint": "https://192.168.10.50:8006/api2/json",
        "proxmox_user": "pve-admin@pam",
        "proxmox_token_id": "vmotion-test",
        "proxmox_token_secret": "test-secret-token",
        "proxmox_verify_ssl": False
    }
    # Test valid operator key
    res = client.post(
        "/api/cluster/config",
        json=payload,
        headers={"X-Operator-Key": "vmotion-operator-key-default"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["proxmox"]["endpoint"] == "https://192.168.10.50:8006/api2/json"
    assert data["proxmox"]["user"] == "pve-admin@pam"
    assert data["proxmox"]["token_secret_configured"] is True
    assert "token_secret" not in data["proxmox"]


def test_api_cluster_config_unauthorized_blocked():
    payload = {"proxmox_endpoint": "https://attacker.evil:8006/api2/json"}
    # Missing or wrong operator key
    res = client.post("/api/cluster/config", json=payload, headers={"X-Operator-Key": "wrong-key"})
    assert res.status_code == 401
    assert "Unauthorized" in res.json()["detail"]


def test_api_test_connection_simulation():
    res = client.post("/api/cluster/test-connection", json={"provider_type": "simulation"})
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "simulation"
    assert data["status"] == "CONNECTED"
    assert data["node_count"] >= 3
    assert data["vm_count"] >= 6


def test_api_test_connection_proxmox_unconfigured():
    # Pass empty secret to verify UNAVAILABLE diagnostics
    res = client.post("/api/cluster/test-connection", json={
        "provider_type": "proxmox",
        "proxmox_endpoint": "https://10.0.0.1:8006/api2/json",
        "proxmox_token_secret": " "
    })
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "proxmox"
    assert data["status"] == "UNAVAILABLE"
    assert "configured" in data["message"]


def test_api_test_connection_libvirt():
    res = client.post("/api/cluster/test-connection", json={
        "provider_type": "libvirt",
        "libvirt_uri": "qemu+ssh://nonexistent@127.0.0.1/system"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "libvirt"
    # On Windows without libvirt-python bindings, status is UNAVAILABLE
    assert data["status"] in ("UNAVAILABLE", "DISCONNECTED", "AUTHENTICATION_ERROR")


def test_api_cluster_telemetry():
    res = client.get("/api/cluster/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "avg_cluster_cpu_percent" in data
    assert "cluster_cpu_imbalance_std" in data
    assert "jains_fairness_cpu" in data
    assert "node_profiles" in data
    assert "vm_profiles" in data
    assert len(data["node_profiles"]) >= 3
    # Check node profile attributes
    first_node = next(iter(data["node_profiles"].values()))
    assert "current_cpu_percent" in first_node
    assert "cpu_moving_avg" in first_node
    assert "cpu_trend" in first_node
    assert first_node["cpu_trend"] in ("rising", "falling", "stable")


def test_api_ai_model_health():
    res = client.get("/api/ai/model/health")
    assert res.status_code == 200
    data = res.json()
    assert "model_loaded" in data
    assert "status_message" in data
    assert "observation_dimension" in data
    assert data["observation_dimension"] == 103
    assert data["action_space_size"] == 7
    if data["model_loaded"]:
        assert data["health_state"] == "MODEL READY"
        assert "PPO MODEL AVAILABLE" in data["status_message"]
        assert data["baseline_fallback_active"] is False
    else:
        assert data["baseline_fallback_active"] is True
        assert "PPO MODEL NOT LOADED / BASELINE ACTIVE" in data["status_message"]
    assert data["baseline_policy_reward_expected"] == 860.6


def test_api_live_mode_switch_requires_confirmation():
    # Attempting to switch to live mode without confirm_live flag must return 400
    res = client.post(
        "/api/cluster/mode",
        json={"provider_type": "proxmox"},
        headers={"X-Operator-Key": "vmotion-operator-key-default"}
    )
    assert res.status_code == 400
    assert "confirmation required" in res.json()["detail"].lower()


def test_api_live_mode_switch_requires_operator_key():
    # Attempting to switch to live mode without valid X-Operator-Key must return 401
    res = client.post(
        "/api/cluster/mode",
        json={"provider_type": "proxmox", "confirm_live": True},
        headers={"X-Operator-Key": "wrong-key"}
    )
    assert res.status_code == 401
    assert "unauthorized" in res.json()["detail"].lower()


def test_api_cancel_migration_endpoint():
    import asyncio
    from app.engine.base import Recommendation
    from app.api.routes import migration_mgr, active_provider

    # 1. Ensure a valid proposal is in PENDING_APPROVAL state in the planner
    rec = Recommendation(
        action_type="MIGRATE",
        vm_id="vm-101",
        source_node="node-01",
        target_node="node-02",
        confidence_score=0.95,
        reason="Test migration proposal for cancellation",
        engine_type="PPO_POLICY"
    )
    cluster = asyncio.run(active_provider.get_cluster_state())
    proposal = migration_mgr.evaluate_and_propose(rec, cluster)
    assert proposal is not None
    proposal_id = proposal.proposal_id

    # 2. Cancel the proposal via API
    cancel_res = client.post(
        f"/api/migrations/cancel/{proposal_id}",
        json={"reason": "Operator maintenance override"}
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["status"] == "cancelled"
    assert data["proposal"]["status"] == "CANCELLED"

    # 3. Subsequent attempt to approve a cancelled proposal must fail with 400 (InvalidStateTransitionError)
    approve_res = client.post(f"/api/migrations/approve/{proposal_id}")
    assert approve_res.status_code == 400
    assert "invalid state transition" in approve_res.json()["detail"].lower()



