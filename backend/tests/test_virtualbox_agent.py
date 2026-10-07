"""
Unit tests for the VirtualBox Host Agent (vmotion-agent).
Verifies health, host metrics, VM inventory, teleporter preparation,
teleport execution, authentication, and error handling.
"""
import pytest
import sys
import os

# Add vmotion-agent to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vmotion-agent")))

from starlette.testclient import TestClient
from agent import app, verify_auth
from unittest.mock import patch

client = TestClient(app)


def test_agent_unauthorized_without_secret():
    res = client.get("/agent/health")
    assert res.status_code == 401
    assert "Unauthorized" in res.json()["detail"]


def test_agent_health_authenticated():
    with patch("agent.run_vbox") as mock_vbox:
        mock_vbox.return_value = (0, "7.2.16", "")
        res = client.get("/agent/health", headers={"X-Agent-Secret": "vmotion-vbox-secret"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert data["vbox_installed"] is True
        assert data["vbox_version"] == "7.2.16"


def test_agent_host_metrics():
    res = client.get("/agent/host", headers={"X-Agent-Secret": "vmotion-vbox-secret"})
    assert res.status_code == 200
    data = res.json()
    assert "cpu_count" in data
    assert "cpu_percent" in data
    assert "ram_total_mb" in data


def test_agent_vms_listing():
    with patch("agent.run_vbox") as mock_vbox:
        # First call: list vms, Second call: list runningvms
        mock_vbox.side_effect = [
            (0, '"DemoVM" {4a8e2b9c-5f3d-4c8e-a9b1-2c3d4e5f6a7b}', ""),
            (0, '"DemoVM" {4a8e2b9c-5f3d-4c8e-a9b1-2c3d4e5f6a7b}', "")
        ]
        res = client.get("/agent/vms", headers={"X-Agent-Secret": "vmotion-vbox-secret"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["running"] == 1
        assert data["vms"][0]["name"] == "DemoVM"
        assert data["vms"][0]["status"] == "running"


def test_agent_teleport_prepare():
    with patch("agent.run_vbox") as mock_vbox:
        mock_vbox.return_value = (0, "", "")
        payload = {"vm_id": "DemoVM", "port": 60050}
        res = client.post("/agent/teleport/prepare", json=payload, headers={"X-Agent-Secret": "vmotion-vbox-secret"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["teleporter_port"] == 60050


def test_agent_teleport_start():
    with patch("agent.run_vbox") as mock_vbox:
        mock_vbox.return_value = (0, "Teleportation 100% completed", "")
        payload = {
            "vm_id": "DemoVM",
            "target_host": "192.168.1.101",
            "port": 60050,
            "max_downtime_ms": 500
        }
        res = client.post("/agent/teleport/start", json=payload, headers={"X-Agent-Secret": "vmotion-vbox-secret"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["completed"] is True
        assert "task_id" in data
