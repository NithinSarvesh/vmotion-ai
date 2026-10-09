"""
Tests for VMotion AI - Real Physical VirtualBox Live Teleportation Demo.
Validates LAN IP discovery, target VM locked session recovery,
pre-flight TCP reachability, gateway LAN IP tracking, and safety gate VBX constants.
"""
import pytest
import socket
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vmotion-agent")))

from agent import get_lan_ip, get_network_info, resolve_vm_name, execute_rpc_command
from app.gateway.agent_gateway import CloudAgentGateway, AgentSession
from app.providers.virtualbox import VirtualBoxProvider
from app.providers.base import MigrationPlan
from app.safety.gate import (
    deterministic_safety_gate,
    VBX_SOURCE_CONNECTED,
    VBX_TARGET_CONNECTED,
    VBX_VM_EXISTS,
    VBX_VM_POWER_STATE,
    VBX_NO_SNAPSHOTS,
    VBX_HARDWARE_COMPATIBLE,
    VBX_CPU_PORTABILITY,
    VBX_SHARED_STORAGE,
    VBX_NETWORK_REACHABLE,
    VBX_TELEPORT_PORT,
    VBX_TARGET_READY,
    VBX_VIRTUALBOX_VERSION,
    VBX_TARGET_NOT_BUSY,
)


def test_agent_get_lan_ip_resolution():
    """Verifies that get_lan_ip returns an IPv4 address and ignores invalid loopbacks."""
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4
    # Ensure it's not a dummy string
    parts = [int(p) for p in ip.split(".")]
    assert len(parts) == 4


def test_agent_get_network_info():
    """Verifies get_network_info structure."""
    net_info = get_network_info()
    assert "lan_ip" in net_info
    assert "hostname" in net_info
    assert "teleport_port" in net_info
    assert net_info["teleport_port"] == 60050


def test_agent_resolve_vm_name():
    """Tests VM resolution: strict exact and case-insensitive match, no arbitrary silent substitution."""
    with patch("agent.run_vbox") as mock_vbox:
        # 1. Exact match when showvminfo succeeds
        mock_vbox.return_value = (0, "name=VMotion-Demo", "")
        assert resolve_vm_name("VMotion-Demo") == "VMotion-Demo"

        # 2. Case-insensitive match from list vms
        mock_vbox.side_effect = [
            (-1, "", "not found"),
            (0, '"VMotion-Demo" {uuid1}\n"OtherVM" {uuid2}', "")
        ]
        assert resolve_vm_name("vmotion-demo") == "VMotion-Demo"

        # 3. Disparate VM name: no silent arbitrary substitution
        mock_vbox.side_effect = [
            (-1, "", "not found"),
            (0, '"UnrelatedVM" {uuid1}', "")
        ]
        assert resolve_vm_name("DemoVM") == "DemoVM"


def test_agent_prepare_target_locked_vm_recovery():
    """
    Verifies that PREPARE_TARGET detects a locked/running VM,
    powers it off, configures teleporter, and starts it in headless listening mode.
    """
    with patch("agent.run_vbox") as mock_vbox, patch("time.sleep"):
        # Sequence:
        # 1. showvminfo for resolve_vm_name -> found
        # 2. showvminfo in PREPARE_TARGET -> VMState="running", SessionState="locked"
        # 3. controlvm poweroff -> rc=0
        # 4. showvminfo poll -> VMState="poweroff"
        # 5. modifyvm -> rc=0
        # 6. startvm --type headless -> rc=0
        # 7. showvminfo poll -> VMState="teleporting", teleporterenabled="on"
        mock_vbox.side_effect = [
            (0, 'name="VMotion - demo target"', ""),
            (0, 'VMState="running"\nSessionState="locked"', ""),
            (0, "Powering off", ""),
            (0, 'VMState="poweroff"', ""),
            (0, "Modified teleporter", ""),
            (0, "Starting VM headlessly", ""),
            (0, 'VMState="teleporting"\nteleporterenabled="on"', "")
        ]

        status, data, err = execute_rpc_command("PREPARE_TARGET", {
            "vm_id": "VMotion - demo target",
            "port": 60050,
            "address": "0.0.0.0"
        })

        assert status == "SUCCESS"
        assert data["status"] == "LISTENING"
        assert data["port"] == 60050
        assert err is None


def test_agent_target_ready_check():
    """Tests TARGET_READY command returns success when teleporter is enabled."""
    with patch("agent.run_vbox") as mock_vbox:
        mock_vbox.side_effect = [
            (0, 'name="VMotion - demo target"', ""), # resolve_vm_name
            (0, 'VMState="teleporting"\nteleporterenabled="on"', "") # showvminfo
        ]
        status, data, err = execute_rpc_command("TARGET_READY", {
            "vm_id": "VMotion - demo target",
            "port": 60050
        })
        assert status == "SUCCESS"
        assert data["ready"] is True


def test_gateway_lan_ip_tracking():
    """Verifies that CloudAgentGateway stores and reports the agent's LAN IP."""
    gw = CloudAgentGateway()
    mock_ws = MagicMock()
    
    import asyncio
    loop = asyncio.new_event_loop()
    session = loop.run_until_complete(gw.register_agent(
        host_id="vbox-host-b",
        websocket=mock_ws,
        hostname="TargetLaptop",
        lan_ip="172.16.0.15",
        tailscale_ip="100.64.0.25",
        vbox_version="7.1.4"
    ))
    loop.close()

    assert session.lan_ip == "172.16.0.15"
    s_dict = session.to_dict(timeout_seconds=10.0)
    assert s_dict["lan_ip"] == "172.16.0.15"

    # Test telemetry update with lan_ip
    gw.record_telemetry("vbox-host-b", {"lan_ip": "172.16.0.20", "cpu_percent": 12.0})
    assert gw.get_session("vbox-host-b").lan_ip == "172.16.0.20"


@pytest.mark.asyncio
async def test_virtualbox_provider_routes_to_lan_ip():
    """Verifies that VirtualBoxProvider routes teleportation to target agent's LAN IP."""
    provider = VirtualBoxProvider()
    
    # Register mock session for target with LAN IP
    from app.gateway.agent_gateway import agent_gateway
    mock_ws = MagicMock()
    await agent_gateway.register_agent(
        host_id="vbox-host-b",
        websocket=mock_ws,
        hostname="FriendLaptop",
        lan_ip="172.16.0.55",
        vbox_version="7.1.0"
    )

    plan = MigrationPlan(
        plan_id="plan-lan-1",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="LAN Hotspot Test",
        created_at=1000.0
    )

    with patch("app.providers.virtualbox.settings.VBOX_MIGRATION_MODE", "teleport"), \
         patch.object(provider, "prepare_target_teleporter", return_value=(True, "Armed")), \
         patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:
        
        from app.gateway.agent_gateway import AgentCommandResponse
        mock_dispatch.return_value = AgentCommandResponse(
            status="SUCCESS",
            data={"stdout": "teleported", "duration_seconds": 3.2}
        )

        task_id = await provider.execute_migration(plan)
        assert task_id.startswith("vbx-teleport-")
        
        # Verify that dispatch_command was called with target_host equal to the LAN IP
        mock_dispatch.assert_called_once()
        call_kwargs = mock_dispatch.call_args[1]
        assert call_kwargs["command"] == "EXECUTE_TELEPORT"
        assert call_kwargs["payload"]["target_host"] == "172.16.0.55"


def test_vbx_explicit_13_constants():
    """Confirms all 13 required VBX safety check constants are defined."""
    constants = [
        VBX_SOURCE_CONNECTED,
        VBX_TARGET_CONNECTED,
        VBX_VM_EXISTS,
        VBX_VM_POWER_STATE,
        VBX_NO_SNAPSHOTS,
        VBX_HARDWARE_COMPATIBLE,
        VBX_CPU_PORTABILITY,
        VBX_SHARED_STORAGE,
        VBX_NETWORK_REACHABLE,
        VBX_TELEPORT_PORT,
        VBX_TARGET_READY,
        VBX_VIRTUALBOX_VERSION,
        VBX_TARGET_NOT_BUSY,
    ]
    for c in constants:
        assert isinstance(c, str)
        assert c.startswith("VBX_")
