"""
Unit tests for CloudAgentGateway and agent RPC dispatch system.
Verifies registration, heartbeat tracking, command dispatch, correlation ID resolution,
timeout handling, offline error handling, and unregistration.
"""
import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock

from app.gateway.agent_gateway import (
    CloudAgentGateway,
    AgentSession,
    AgentOfflineError,
    AgentCommandTimeoutError,
    AgentCommandResponse
)


@pytest.fixture
def gateway():
    return CloudAgentGateway()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_agent_registration_and_status(gateway, mock_ws):
    session = await gateway.register_agent(
        host_id="host-a",
        hostname="Laptop-Alpha",
        tailscale_ip="100.64.0.10",
        websocket=mock_ws
    )
    assert session.agent_id == "host-a"
    assert session.hostname == "Laptop-Alpha"
    assert session.tailscale_ip == "100.64.0.10"
    assert gateway.is_agent_online("host-a") is True
    assert gateway.is_agent_online("host-b") is False

    active = gateway.list_active_agents()
    assert len(active) == 1
    assert active[0]["host_id"] == "host-a"
    assert active[0]["tailscale_ip"] == "100.64.0.10"
    assert active[0]["status"] == "online"


def test_agent_session_heartbeat_freshness(mock_ws):
    session = AgentSession(
        host_id="host-test",
        websocket=mock_ws,
        hostname="Laptop-Test",
        tailscale_ip="100.64.0.99"
    )
    assert session.is_alive(timeout_seconds=5.0) is True

    # Simulate expired heartbeat
    session.last_heartbeat_at = time.time() - 10.0
    assert session.is_alive(timeout_seconds=5.0) is False


@pytest.mark.asyncio
async def test_agent_heartbeat_and_telemetry_recording(gateway, mock_ws):
    await gateway.register_agent("host-b", mock_ws, hostname="Laptop-Beta", tailscale_ip="100.64.0.20")
    gateway.record_heartbeat("host-b", latency_ms=12.5)

    telemetry_payload = {
        "cpu_percent": 22.4,
        "ram_percent": 45.1,
        "vms": [{"name": "DemoVM", "status": "running"}]
    }
    gateway.update_telemetry("host-b", telemetry_payload)

    session = gateway.get_session("host-b")
    assert session is not None
    assert session.latest_telemetry["cpu_percent"] == 22.4


@pytest.mark.asyncio
async def test_dispatch_command_success(gateway, mock_ws):
    await gateway.register_agent("host-a", mock_ws, hostname="Laptop-Alpha", tailscale_ip="100.64.0.10")

    # Coroutine that simulates agent receiving message and replying
    async def simulate_agent_reply():
        await asyncio.sleep(0.01)
        assert mock_ws.send_json.called
        sent_data = mock_ws.send_json.call_args[0][0]
        corr_id = sent_data["correlation_id"]
        assert sent_data["command"] == "PREFLIGHT"

        # Agent sends back resolution
        gateway.resolve_response(
            correlation_id=corr_id,
            status="SUCCESS",
            data={"vm_exists": True, "storage_accessible": True},
            error=None
        )

    task = asyncio.create_task(simulate_agent_reply())

    resp = await gateway.dispatch_command(
        agent_id="host-a",
        command="PREFLIGHT",
        payload={"vm_id": "DemoVM"},
        timeout_seconds=2.0
    )
    await task

    assert resp.status == "SUCCESS"
    assert resp.data["vm_exists"] is True
    assert resp.data["storage_accessible"] is True
    assert resp.error is None


@pytest.mark.asyncio
async def test_dispatch_command_offline_error(gateway):
    with pytest.raises(AgentOfflineError) as exc_info:
        await gateway.dispatch_command(
            agent_id="host-nonexistent",
            command="PING",
            payload={}
        )
    assert "offline" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_dispatch_command_timeout(gateway, mock_ws):
    await gateway.register_agent("host-a", mock_ws, hostname="Laptop-Alpha", tailscale_ip="100.64.0.10")

    # Don't resolve the command; expect timeout
    with pytest.raises(AgentCommandTimeoutError) as exc_info:
        await gateway.dispatch_command(
            agent_id="host-a",
            command="PREPARE_TARGET",
            payload={"vm_id": "DemoVM"},
            timeout_seconds=0.1
        )
    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_agent_unregistration_cancels_futures(gateway, mock_ws):
    await gateway.register_agent("host-a", mock_ws, hostname="Laptop-Alpha", tailscale_ip="100.64.0.10")

    # Launch a dispatch
    dispatch_coro = gateway.dispatch_command(
        agent_id="host-a",
        command="PING",
        payload={},
        timeout_seconds=5.0
    )
    task = asyncio.create_task(dispatch_coro)
    await asyncio.sleep(0.01)

    # Unregister agent while future is pending
    await gateway.unregister_agent("host-a")

    assert gateway.is_agent_online("host-a") is False
    with pytest.raises(AgentOfflineError):
        await task
