"""
Automated unit and integration tests for Gateway Authentication, Settings Sync,
Agent Token Resolution, and Setup Script Pre-Flight Validations.
"""
import os
import re
import pytest
from pathlib import Path
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.config import Settings, settings


client = TestClient(app)


def test_gateway_auth_success_with_query_param():
    """Agent connects with valid token in query param and successfully handshakes."""
    token = settings.GATEWAY_AGENT_TOKEN
    with client.websocket_connect(f"/ws/agent?host_id=vbox-host-a&token={token}") as ws:
        # Send registration packet
        ws.send_json({
            "type": "REGISTER",
            "host_id": "vbox-host-a",
            "hostname": "Test-Laptop-A",
            "lan_ip": "192.168.1.50",
            "vbox_version": "7.0.14"
        })
        resp = ws.receive_json()
        assert resp["type"] == "REGISTERED"
        assert resp["host_id"] == "vbox-host-a"
        assert resp["status"] == "ONLINE"


def test_gateway_auth_success_with_header():
    """Agent connects with valid token in X-Agent-Secret header and successfully handshakes."""
    token = settings.GATEWAY_AGENT_TOKEN
    with client.websocket_connect(
        "/ws/agent?host_id=vbox-host-b",
        headers={"X-Agent-Secret": token}
    ) as ws:
        ws.send_json({
            "type": "REGISTER",
            "host_id": "vbox-host-b",
            "hostname": "Test-Laptop-B",
            "lan_ip": "192.168.1.51"
        })
        resp = ws.receive_json()
        assert resp["type"] == "REGISTERED"
        assert resp["host_id"] == "vbox-host-b"


def test_gateway_auth_rejection_missing_token():
    """Agent connection without any token is rejected with WebSocket close code 4001."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/agent?host_id=vbox-host-unknown") as ws:
            pass
    assert exc_info.value.code == 4001


def test_gateway_auth_rejection_invalid_token():
    """Agent connection with incorrect token is rejected with WebSocket close code 4001."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/agent?host_id=vbox-host-a&token=completely-invalid-secret") as ws:
            pass
    assert exc_info.value.code == 4001


def test_gateway_auth_rejection_invalid_header_token():
    """Agent connection with incorrect header token is rejected with WebSocket close code 4001."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/agent?host_id=vbox-host-a",
            headers={"X-Agent-Secret": "wrong-secret"}
        ) as ws:
            pass
    assert exc_info.value.code == 4001


def test_settings_sync_gateway_token_to_vbox_secret():
    """When GATEWAY_AGENT_TOKEN is customized, VBOX_AGENT_SECRET synchronizes automatically."""
    cfg = Settings(GATEWAY_AGENT_TOKEN="custom-render-generated-token-12345")
    assert cfg.GATEWAY_AGENT_TOKEN == "custom-render-generated-token-12345"
    assert cfg.VBOX_AGENT_SECRET == "custom-render-generated-token-12345"


def test_settings_sync_vbox_secret_to_gateway_token():
    """When VBOX_AGENT_SECRET is customized, GATEWAY_AGENT_TOKEN synchronizes automatically."""
    cfg = Settings(VBOX_AGENT_SECRET="custom-vbox-secret-67890")
    assert cfg.VBOX_AGENT_SECRET == "custom-vbox-secret-67890"
    assert cfg.GATEWAY_AGENT_TOKEN == "custom-vbox-secret-67890"


def test_agent_py_token_resolution_precedence(monkeypatch):
    """Verify agent.py token resolution: VMOTION_AGENT_SECRET > GATEWAY_AGENT_TOKEN > default."""
    # Test VMOTION_AGENT_SECRET precedence
    monkeypatch.setenv("VMOTION_AGENT_SECRET", "secret-from-vmotion")
    monkeypatch.setenv("GATEWAY_AGENT_TOKEN", "secret-from-gateway")
    resolved = os.getenv("VMOTION_AGENT_SECRET") or os.getenv("GATEWAY_AGENT_TOKEN") or "vmotion-vbox-secret"
    assert resolved == "secret-from-vmotion"

    # Test GATEWAY_AGENT_TOKEN fallback
    monkeypatch.delenv("VMOTION_AGENT_SECRET", raising=False)
    monkeypatch.setenv("GATEWAY_AGENT_TOKEN", "secret-from-gateway")
    resolved = os.getenv("VMOTION_AGENT_SECRET") or os.getenv("GATEWAY_AGENT_TOKEN") or "vmotion-vbox-secret"
    assert resolved == "secret-from-gateway"

    # Test default fallback
    monkeypatch.delenv("GATEWAY_AGENT_TOKEN", raising=False)
    resolved = os.getenv("VMOTION_AGENT_SECRET") or os.getenv("GATEWAY_AGENT_TOKEN") or "vmotion-vbox-secret"
    assert resolved == "vmotion-vbox-secret"


def test_setup_host_a_script_contract():
    """Verify setup_host_a_source.ps1 enforces elevation, verified firewall, and secure token."""
    script_path = Path("scripts/setup_host_a_source.ps1")
    assert script_path.exists(), "Host A script must exist"
    content = script_path.read_text(encoding="utf-8")

    # 1. Parameter accepts GatewayToken
    assert re.search(r"\[string\]\$GatewayToken\s*=\s*\"\"", content), "Must have GatewayToken parameter"

    # 2. Elevation check fails closed with exit 1
    assert "Administrator" in content
    assert "exit 1" in content

    # 3. Secure token resolution
    assert "VMOTION_AGENT_SECRET" in content
    assert "GATEWAY_AGENT_TOKEN" in content
    assert "Read-Host" in content and "-AsSecureString" in content
    assert "onrender.com" in content and "vmotion-vbox-secret" in content

    # 4. Firewall rule uses -ErrorAction Stop and verifies Enabled -eq 'True'
    assert "-ErrorAction Stop" in content
    assert "Get-NetFirewallRule" in content
    assert ".Enabled -eq 'True'" in content

    # 5. Pre-flight verification summary
    assert "PRE-FLIGHT VERIFICATION" in content


def test_setup_host_b_script_contract():
    """Verify setup_host_b_target.ps1 enforces elevation, disk space, strict SMB access, and secure token."""
    script_path = Path("scripts/setup_host_b_target.ps1")
    assert script_path.exists(), "Host B script must exist"
    content = script_path.read_text(encoding="utf-8")

    # 1. Parameter accepts GatewayToken
    assert re.search(r"\[string\]\$GatewayToken\s*=\s*\"\"", content), "Must have GatewayToken parameter"

    # 2. Elevation check fails closed with exit 1
    assert "Administrator" in content
    assert "exit 1" in content

    # 3. Secure token resolution
    assert "VMOTION_AGENT_SECRET" in content
    assert "GATEWAY_AGENT_TOKEN" in content
    assert "Read-Host" in content and "-AsSecureString" in content
    assert "onrender.com" in content and "vmotion-vbox-secret" in content

    # 4. Staging storage, disk quota (>= 5.0 GB), write permissions, and fail-closed SMB share verification
    assert "C:\\VMotionStaging" in content
    assert "5.0" in content
    assert ".vmotion_write_test" in content
    assert "Test-Path $sharedPath" in content
    assert "Write-Error" in content
    assert "Port 60050 receiver not required" in content

    # 5. Pre-flight verification summary
    assert "PRE-FLIGHT VERIFICATION" in content
