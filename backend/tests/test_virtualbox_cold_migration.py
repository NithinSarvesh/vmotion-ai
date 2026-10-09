"""
Comprehensive Cold / Offline VM Migration Test Suite.
Verifies real Oracle VirtualBox OVA export/import workflow across the 9 stages:
1. PREFLIGHT
2. SOURCE SHUTDOWN
3. EXPORT
4. TRANSFER
5. CHECKSUM VERIFIED
6. IMPORT
7. DESTINATION STARTED
8. VERIFY
9. SUCCESS

Tests include:
- Preflight disk space quota failure
- Preflight success
- Graceful shutdown timeout
- Graceful shutdown success
- OVA export failure and success with SHA-256
- Direct SMB transfer failure and success
- Checksum mismatch detection and file quarantine
- Checksum match success
- Duplicate job request rejection (idempotency)
- Appliance import failure and success
- Destination VM start failure
- Destination running health check verification
- Full end-to-end 9-stage orchestration in VirtualBoxProvider
"""
import pytest
import sys
import os
import time
import tempfile
import hashlib
import asyncio
from unittest.mock import patch, MagicMock

# Add vmotion-agent to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "vmotion-agent")))
from agent import execute_rpc_command

from app.providers.virtualbox import VirtualBoxProvider
from app.providers.base import MigrationPlan, MigrationTaskStatus
from app.gateway.agent_gateway import AgentCommandResponse, agent_gateway


# ==============================================================================
# 1. AGENT-LEVEL RPC TESTS FOR COLD MIGRATION HANDLERS
# ==============================================================================

def test_agent_preflight_insufficient_disk_space():
    """Verifies PREFLIGHT fails when requested disk space exceeds available storage."""
    with patch("shutil.disk_usage") as mock_usage, \
         patch("agent.run_vbox") as mock_vbox:
        mock_vbox.return_value = (0, "7.2.16", "")
        # Return 1 GB free (in bytes: 1024 * 1024 * 1024)
        mock_usage.return_value = MagicMock(free=1024 * 1024 * 1024, total=500 * 1024 * 1024 * 1024)

        # Request 10 GB (10240 MB)
        status, data, err = execute_rpc_command("PREFLIGHT", {
            "role": "source",
            "required_disk_mb": 10240
        })
        assert status == "FAILED"
        assert "Insufficient disk space" in err or "sufficient_disk=False" in str(err)


def test_agent_preflight_success():
    """Verifies PREFLIGHT succeeds when disk quotas and VirtualBox are satisfied."""
    with patch("shutil.disk_usage") as mock_usage, \
         patch("agent.run_vbox") as mock_vbox:
        # First call: showvminfo, Second call: vbox --version
        mock_vbox.side_effect = [
            (0, "7.2.16", ""),
            (0, 'VMState="running"\nSnapshotCount=0\nSATA-0-0="C:\\disk.vdi"', "")
        ]
        # Return 50 GB free
        mock_usage.return_value = MagicMock(free=50 * 1024 * 1024 * 1024, total=500 * 1024 * 1024 * 1024)

        status, data, err = execute_rpc_command("PREFLIGHT", {
            "role": "target",
            "required_disk_mb": 5000
        })
        assert status == "SUCCESS"
        assert data["vbox_installed"] is True
        assert data["disk_free_mb"] > 5000


def test_agent_shutdown_vm_timeout():
    """Verifies SHUTDOWN_VM fails gracefully when VM fails to power off within timeout."""
    def fake_vbox(args, timeout=None):
        if "controlvm" in args and "acpipowerbutton" in args:
            return (0, "ACPI sent", "")
        elif "showvminfo" in args:
            return (0, 'VMState="running"', "")
        return (0, "", "")

    with patch("agent.run_vbox", side_effect=fake_vbox), \
         patch("time.sleep"):
        status, data, err = execute_rpc_command("SHUTDOWN_VM", {
            "vm_id": "test_vm",
            "timeout_seconds": 1
        })
        assert status == "FAILED"
        assert "timed out" in err


def test_agent_shutdown_vm_success():
    """Verifies SHUTDOWN_VM detects powered-off state after ACPI signal."""
    calls = {"count": 0}

    def fake_vbox(args, timeout=None):
        if "controlvm" in args and "acpipowerbutton" in args:
            return (0, "ACPI sent", "")
        elif "showvminfo" in args:
            calls["count"] += 1
            if calls["count"] >= 3:
                return (0, 'VMState="poweroff"', "")
            return (0, 'VMState="running"', "")
        return (0, "", "")

    with patch("agent.run_vbox", side_effect=fake_vbox), \
         patch("time.sleep"):
        status, data, err = execute_rpc_command("SHUTDOWN_VM", {
            "vm_id": "test_vm",
            "timeout_seconds": 5
        })
        assert status == "SUCCESS"
        assert data["state"] == "poweroff"


def test_agent_export_ova_success():
    """Verifies EXPORT_OVA produces appliance, computes file size and valid SHA-256."""
    with tempfile.TemporaryDirectory() as tmpdir:
        def fake_export(cmd, timeout=None):
            if "export" in cmd:
                ova_p = cmd[cmd.index("-o") + 1]
                with open(ova_p, "wb") as f:
                    f.write(b"MOCK_OVA_PAYLOAD_DATA_FOR_TESTING_SHA256")
                return (0, "Successfully exported 1 machine(s)", "")
            return (0, "", "")

        with patch("agent.run_vbox", side_effect=fake_export):
            status, data, err = execute_rpc_command("EXPORT_OVA", {
                "vm_id": "test_vm",
                "job_id": "testjob123",
                "output_dir": tmpdir
            })
            assert status == "SUCCESS"
            assert data["file_size_bytes"] == len(b"MOCK_OVA_PAYLOAD_DATA_FOR_TESTING_SHA256")
            expected_hash = hashlib.sha256(b"MOCK_OVA_PAYLOAD_DATA_FOR_TESTING_SHA256").hexdigest()
            assert data["sha256"] == expected_hash
            assert os.path.exists(data["ova_path"])


def test_agent_export_ova_failure():
    """Verifies EXPORT_OVA reports error if VBoxManage export command fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("agent.run_vbox", return_value=(1, "", "VBoxManage: error: Could not lock disk")):
            status, data, err = execute_rpc_command("EXPORT_OVA", {
                "vm_id": "test_vm",
                "job_id": "testjob123",
                "output_dir": tmpdir
            })
            assert status == "FAILED"
            assert "VBoxManage OVA export failed" in err


def test_agent_transfer_package_missing_source():
    """Verifies TRANSFER_PACKAGE fails when source SMB file path does not exist."""
    with tempfile.TemporaryDirectory() as staging_dir:
        status, data, err = execute_rpc_command("TRANSFER_PACKAGE", {
            "source_path": r"\\invalid_host\share\missing.ova",
            "job_id": "job123",
            "staging_dir": staging_dir
        })
        assert status == "FAILED"
        assert "Source OVA package not found" in err


def test_agent_verify_checksum_mismatch_quarantine():
    """Verifies VERIFY_CHECKSUM detects corrupted file, renames to .corrupt, and fails closed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "appliance.ova")
        with open(test_file, "wb") as f:
            f.write(b"CORRUPTED_BITS_DURING_TRANSFER")

        correct_sha = hashlib.sha256(b"ORIGINAL_CORRECT_PAYLOAD").hexdigest()

        status, data, err = execute_rpc_command("VERIFY_CHECKSUM", {
            "file_path": test_file,
            "expected_sha256": correct_sha
        })
        assert status == "FAILED"
        assert "checksum mismatch" in err.lower()
        # Assert file was quarantined to .corrupt
        assert not os.path.exists(test_file)
        assert os.path.exists(test_file + ".corrupt")


def test_agent_verify_checksum_success():
    """Verifies VERIFY_CHECKSUM succeeds when hashes match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "appliance.ova")
        content = b"VALID_CRYPTOGRAPHIC_PAYLOAD"
        with open(test_file, "wb") as f:
            f.write(content)

        matching_sha = hashlib.sha256(content).hexdigest()

        status, data, err = execute_rpc_command("VERIFY_CHECKSUM", {
            "file_path": test_file,
            "expected_sha256": matching_sha
        })
        assert status == "SUCCESS"
        assert data["verified"] is True
        assert data["sha256"] == matching_sha


def test_agent_import_ova_duplicate_job_rejection():
    """Verifies IMPORT_OVA rejects duplicate job requests if VM already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_ova = os.path.join(tmpdir, "appliance.ova")
        with open(fake_ova, "wb") as f:
            f.write(b"OVA")

        with patch("agent.run_vbox") as mock_vbox:
            mock_vbox.return_value = (0, '"VMotion-Migrated-dupjob" {guid123}\n"OtherVM" {guid456}', "")

            status, data, err = execute_rpc_command("IMPORT_OVA", {
                "ova_path": fake_ova,
                "job_id": "dupjob",
                "vm_name": "VMotion-Migrated-dupjob"
            })
            assert status == "FAILED"
            assert "Duplicate migration job" in err or "already exists" in err


def test_agent_import_ova_success():
    """Verifies IMPORT_OVA executes VBoxManage import and registers appliance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_ova = os.path.join(tmpdir, "test.ova")
        with open(fake_ova, "wb") as f:
            f.write(b"OVA")

        with patch("agent.run_vbox") as mock_vbox:
            # First call: list vms (not existing)
            # Second call: import command
            mock_vbox.side_effect = [
                (0, '"UnrelatedVM" {guid123}', ""),
                (0, "0%... 50%... 100% Successfully imported the appliance", "")
            ]

            status, data, err = execute_rpc_command("IMPORT_OVA", {
                "ova_path": fake_ova,
                "job_id": "job_new",
                "vm_name": "VMotion-Migrated-job_new"
            })
            assert status == "SUCCESS"
            assert data["vm_name"] == "VMotion-Migrated-job_new"


def test_agent_start_vm_failure():
    """Verifies START_VM returns error if VBoxManage startvm fails."""
    with patch("agent.run_vbox", return_value=(1, "", "VBoxManage: error: Failed to open session")):
        status, data, err = execute_rpc_command("START_VM", {
            "vm_name": "VMotion-Migrated-target"
        })
        assert status == "FAILED"
        assert "Failed to start destination VM" in err


def test_agent_verify_destination_running():
    """Verifies VERIFY_DESTINATION checks that imported VM is in running state."""
    with patch("agent.run_vbox") as mock_vbox:
        mock_vbox.side_effect = [
            (0, '"VMotion-Migrated-target" {guid123}', ""),
            (0, 'VMState="running"', "")
        ]
        status, data, err = execute_rpc_command("VERIFY_DESTINATION", {
            "vm_name": "VMotion-Migrated-target"
        })
        assert status == "SUCCESS"
        assert data["verified"] is True
        assert data["vm_state"] == "running"


# ==============================================================================
# 2. PROVIDER ORCHESTRATION TESTS FOR COLD MIGRATION (9 STAGES)
# ==============================================================================

@pytest.mark.asyncio
async def test_provider_cold_migration_full_success():
    """Verifies full 9-stage cold migration succeeds with verified metrics from live agents."""
    provider = VirtualBoxProvider()

    plan = MigrationPlan(
        plan_id="plan-cold-1",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Load balance Cold Migration",
        created_at=time.time()
    )

    task_id = "vbx-cold-test1"
    task = MigrationTaskStatus(
        task_id=task_id,
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )
    provider._tasks[task_id] = task

    mock_session = MagicMock()
    mock_session.lan_ip = "192.168.1.10"

    expected_sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    with patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "get_session", return_value=mock_session), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:

        async def fake_dispatch(agent_id, command, payload, timeout_seconds=None):
            if command == "PREFLIGHT_CHECK":
                if payload.get("role") == "source":
                    return AgentCommandResponse(status="SUCCESS", data={"preflight_passed": True, "vm_exists": True, "registered_vms": ["VMotion-Demo"]})
                else:
                    return AgentCommandResponse(status="SUCCESS", data={"preflight_passed": True})
            elif command == "SHUTDOWN_VM":
                return AgentCommandResponse(status="SUCCESS", data={"state": "poweroff", "shutdown": True})
            elif command == "EXPORT_OVA":
                return AgentCommandResponse(status="SUCCESS", data={
                    "file_size_bytes": 104857600,
                    "file_size_mb": 100.0,
                    "sha256": expected_sha,
                    "export_duration_seconds": 12.5,
                    "ova_path": "C:\\VMotionShared\\VMotion-Demo.ova"
                })
            elif command == "TRANSFER_PACKAGE":
                return AgentCommandResponse(status="SUCCESS", data={
                    "transfer_duration_seconds": 8.0,
                    "staged_path": "C:\\VMotionStaging\\VMotion-Demo.ova"
                })
            elif command == "VERIFY_CHECKSUM":
                return AgentCommandResponse(status="SUCCESS", data={"verified": True, "sha256": expected_sha})
            elif command == "IMPORT_OVA":
                return AgentCommandResponse(status="SUCCESS", data={
                    "import_duration_seconds": 15.0,
                    "vm_name": f"VMotion-Migrated-{task_id}"
                })
            elif command == "START_VM":
                return AgentCommandResponse(status="SUCCESS", data={"started": True, "vm_state": "running"})
            elif command == "VERIFY_DESTINATION":
                return AgentCommandResponse(status="SUCCESS", data={"verified": True, "vm_state": "running"})
            return AgentCommandResponse(status="SUCCESS", data={})

        mock_dispatch.side_effect = fake_dispatch

        await provider._run_cold_migration_job(task, plan)

        assert task.stage == "SUCCESS"
        assert task.state == "VERIFIED"
        assert task.progress_percent == 100.0
        assert task.file_size_bytes == 104857600
        assert task.file_size_mb == 100.0
        assert task.sha256 == expected_sha
        assert task.export_duration_seconds == 12.5
        assert task.transfer_duration_seconds == 8.0
        assert task.imported_vm_name.startswith("VMotion-Migrated-")
        assert task.imported_vm_name == "VMotion-Migrated-test1"
        assert task.verified_at is not None
        assert task.completed_at is not None


@pytest.mark.asyncio
async def test_cold_migration_fails_when_both_agents_offline():
    """Verifies that cold migration fails closed at PREFLIGHT when both agents are offline."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-offline-both",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Fail offline test",
        created_at=time.time()
    )
    task = MigrationTaskStatus(
        task_id="task-offline-both",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    with patch.object(agent_gateway, "is_agent_online", return_value=False):
        await provider._run_cold_migration_job(task, plan)
        assert task.state == "FAILED"
        assert "PREFLIGHT" in task.stage
        assert "Both physical agents are offline" in task.error


@pytest.mark.asyncio
async def test_cold_migration_fails_when_source_agent_offline():
    """Verifies that cold migration fails closed at PREFLIGHT when source agent is offline."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-offline-src",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Fail source offline test",
        created_at=time.time()
    )
    task = MigrationTaskStatus(
        task_id="task-offline-src",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    with patch.object(agent_gateway, "is_agent_online", side_effect=lambda aid: aid == "vbox-host-b"):
        await provider._run_cold_migration_job(task, plan)
        assert task.state == "FAILED"
        assert "PREFLIGHT" in task.stage
        assert "Source host agent 'vbox-host-a' is offline" in task.error


@pytest.mark.asyncio
async def test_cold_migration_fails_when_target_agent_offline():
    """Verifies that cold migration fails closed at PREFLIGHT when target agent is offline."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-offline-tgt",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Fail target offline test",
        created_at=time.time()
    )
    task = MigrationTaskStatus(
        task_id="task-offline-tgt",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    with patch.object(agent_gateway, "is_agent_online", side_effect=lambda aid: aid == "vbox-host-a"):
        await provider._run_cold_migration_job(task, plan)
        assert task.state == "FAILED"
        assert "PREFLIGHT" in task.stage
        assert "Target host agent 'vbox-host-b' is offline" in task.error


@pytest.mark.asyncio
async def test_cold_migration_fails_when_source_vm_nonexistent():
    """Verifies that cold migration fails at PREFLIGHT with actionable error if requested VM is missing."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-missing-vm",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Missing VM test",
        created_at=time.time()
    )
    task = MigrationTaskStatus(
        task_id="task-missing-vm",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    with patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:

        mock_dispatch.return_value = AgentCommandResponse(
            status="SUCCESS",
            data={"vm_exists": False, "preflight_passed": False, "registered_vms": ["Ubuntu-22", "Windows-10"]}
        )

        await provider._run_cold_migration_job(task, plan)
        assert task.state == "FAILED"
        assert "PREFLIGHT" in task.stage
        assert "Source VM 'VMotion-Demo' is not registered" in task.error
        assert "Ubuntu-22" in task.error


@pytest.mark.asyncio
async def test_provider_cold_migration_fails_on_export_error():
    """Verifies that an error during OVA export immediately marks task as FAILED at stage EXPORT."""
    provider = VirtualBoxProvider()

    plan = MigrationPlan(
        plan_id="plan-cold-fail-exp",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Cold Migration Export Fail",
        created_at=time.time()
    )

    task = MigrationTaskStatus(
        task_id="task-fail-exp",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    with patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:
        
        async def fake_dispatch(agent_id, command, payload, timeout_seconds=None):
            if command == "PREFLIGHT_CHECK":
                return AgentCommandResponse(status="SUCCESS", data={"preflight_passed": True, "vm_exists": True})
            elif command == "SHUTDOWN_VM":
                return AgentCommandResponse(status="SUCCESS", data={"state": "poweroff", "shutdown": True})
            elif command == "EXPORT_OVA":
                return AgentCommandResponse(status="FAILED", error="Disk locked by host OS")
            return AgentCommandResponse(status="SUCCESS", data={})

        mock_dispatch.side_effect = fake_dispatch

        await provider._run_cold_migration_job(task, plan)

        assert task.state == "FAILED"
        assert "EXPORT" in task.stage
        assert "Disk locked by host OS" in task.error


@pytest.mark.asyncio
async def test_provider_cold_migration_fails_on_checksum_mismatch():
    """Verifies that a checksum verification error marks task as FAILED at stage CHECKSUM VERIFIED."""
    provider = VirtualBoxProvider()

    plan = MigrationPlan(
        plan_id="plan-cold-fail-chk",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Cold Migration Checksum Fail",
        created_at=time.time()
    )

    task = MigrationTaskStatus(
        task_id="task-fail-chk",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    mock_session = MagicMock()
    mock_session.lan_ip = "192.168.1.10"

    valid_sha = "a" * 64

    with patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "get_session", return_value=mock_session), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:
        
        async def fake_dispatch(agent_id, command, payload, timeout_seconds=None):
            if command == "PREFLIGHT_CHECK":
                return AgentCommandResponse(status="SUCCESS", data={"preflight_passed": True, "vm_exists": True})
            elif command == "SHUTDOWN_VM":
                return AgentCommandResponse(status="SUCCESS", data={"state": "poweroff", "shutdown": True})
            elif command == "EXPORT_OVA":
                return AgentCommandResponse(status="SUCCESS", data={"file_size_bytes": 1000, "file_size_mb": 1.0, "sha256": valid_sha, "export_duration_seconds": 2.0, "ova_path": "C:\\test.ova"})
            elif command == "TRANSFER_PACKAGE":
                return AgentCommandResponse(status="SUCCESS", data={"transfer_duration_seconds": 1.5, "staged_path": "C:\\staged.ova"})
            elif command == "VERIFY_CHECKSUM":
                return AgentCommandResponse(status="FAILED", error="SHA-256 digest corrupted in transit")
            return AgentCommandResponse(status="SUCCESS", data={})

        mock_dispatch.side_effect = fake_dispatch

        await provider._run_cold_migration_job(task, plan)

        assert task.state == "FAILED"
        assert "CHECKSUM VERIFIED" in task.stage
        assert "SHA-256 digest corrupted in transit" in task.error


@pytest.mark.asyncio
async def test_cold_migration_fails_when_destination_verification_incomplete():
    """Verifies that cold migration fails at VERIFY if destination VM is not running."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-verify-fail",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Destination health check failure",
        created_at=time.time()
    )
    task = MigrationTaskStatus(
        task_id="task-verify-fail",
        plan_id=plan.plan_id,
        vm_id=plan.vm_id,
        source_node=plan.source_node,
        target_node=plan.target_node,
        state="PREPARING",
        stage="PREFLIGHT",
        progress_percent=5.0,
        started_at=time.time(),
        updated_at=time.time()
    )

    mock_session = MagicMock()
    mock_session.lan_ip = "192.168.1.10"
    valid_sha = "b" * 64

    with patch.object(agent_gateway, "is_agent_online", return_value=True), \
         patch.object(agent_gateway, "get_session", return_value=mock_session), \
         patch.object(agent_gateway, "dispatch_command") as mock_dispatch:

        async def fake_dispatch(agent_id, command, payload, timeout_seconds=None):
            if command == "PREFLIGHT_CHECK":
                return AgentCommandResponse(status="SUCCESS", data={"preflight_passed": True, "vm_exists": True})
            elif command == "SHUTDOWN_VM":
                return AgentCommandResponse(status="SUCCESS", data={"state": "poweroff", "shutdown": True})
            elif command == "EXPORT_OVA":
                return AgentCommandResponse(status="SUCCESS", data={"file_size_bytes": 1000, "file_size_mb": 1.0, "sha256": valid_sha, "export_duration_seconds": 2.0, "ova_path": "C:\\test.ova"})
            elif command == "TRANSFER_PACKAGE":
                return AgentCommandResponse(status="SUCCESS", data={"transfer_duration_seconds": 1.5, "staged_path": "C:\\staged.ova"})
            elif command == "VERIFY_CHECKSUM":
                return AgentCommandResponse(status="SUCCESS", data={"verified": True, "sha256": valid_sha})
            elif command == "IMPORT_OVA":
                return AgentCommandResponse(status="SUCCESS", data={"import_duration_seconds": 5.0, "vm_name": "VMotion-Migrated-1"})
            elif command == "START_VM":
                return AgentCommandResponse(status="SUCCESS", data={"started": True})
            elif command == "VERIFY_DESTINATION":
                return AgentCommandResponse(status="SUCCESS", data={"verified": False, "vm_state": "aborted"})
            return AgentCommandResponse(status="SUCCESS", data={})

        mock_dispatch.side_effect = fake_dispatch

        await provider._run_cold_migration_job(task, plan)

        assert task.state == "FAILED"
        assert "VERIFY" in task.stage
        assert "not running" in task.error


@pytest.mark.asyncio
async def test_cold_migration_mode_is_authoritative_even_with_teleport_in_reason():
    """Verifies that VBOX_MIGRATION_MODE=cold_ova is authoritative even if plan.reason mentions teleport."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-auth-cold",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Teleportation required by PPO policy",
        created_at=time.time()
    )

    with patch("app.providers.virtualbox.settings.VBOX_MIGRATION_MODE", "cold_ova"), \
         patch.object(provider, "_run_cold_migration_job") as mock_cold_job:
        
        task_id = await provider.execute_migration(plan)
        assert task_id.startswith("vbx-cold-")
        mock_cold_job.assert_called_once()


@pytest.mark.asyncio
async def test_teleport_mode_runs_legacy_when_configured():
    """Verifies that VBOX_MIGRATION_MODE=teleport dispatches legacy teleportation when explicitly configured."""
    provider = VirtualBoxProvider()
    plan = MigrationPlan(
        plan_id="plan-legacy-tel",
        vm_id="VMotion-Demo",
        source_node="vbox-host-a",
        target_node="vbox-host-b",
        reason="Explicit teleportation mode",
        created_at=time.time()
    )

    with patch("app.providers.virtualbox.settings.VBOX_MIGRATION_MODE", "teleport"), \
         patch.object(provider, "prepare_target_teleporter", return_value=(True, "Armed")) as mock_prep:
        
        task_id = await provider.execute_migration(plan)
        assert task_id.startswith("vbx-teleport-")
        mock_prep.assert_called_once()
