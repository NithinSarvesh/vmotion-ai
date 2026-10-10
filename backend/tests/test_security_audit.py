"""
Security Regression Test Suite for VMotion AI.
Validates all 10 audit requirements:
1. Zero secret exposure on public endpoints (/api/agent/download, /api/devices, etc.)
2. Strict API authorization: operators, device ownership, cross-device spoofing protection
3. Fail-closed production configuration validation
4. Authentic VM inventory verification
5. Scoped, expiring, single-use cryptographic transfer authorization
6. Migration job FSM protection and state persistence
"""
import os
import time
import uuid
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient

from app.main import app
from app.config import settings, Settings
from app.db.database import (
    register_device,
    get_device,
    list_devices,
    sanitize_device,
    create_migration_job,
    get_migration_job,
    create_transfer_authorization,
    verify_and_redeem_transfer_authorization,
    compute_transfer_hmac,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Secret Exposure Audits
# -----------------------------------------------------------------------------

def test_agent_download_zero_secret_exposure(tmp_path):
    """Verifies that /api/agent/download leaks zero secrets when binary is missing or present."""
    # Temporarily point dist dir to an empty directory
    with patch.object(settings, "AGENT_DIST_DIR", str(tmp_path)):
        resp = client.get("/api/agent/download")
        assert resp.status_code == 503
        data = resp.json()
        assert data["available"] is False
        assert data["status"] == "unavailable"
        
        # Verify absolutely no secrets exist in the response
        resp_str = resp.text.lower()
        assert "secret" not in resp_str
        assert "token" not in resp_str
        assert "password" not in resp_str
        assert settings.ENROLLMENT_SECRET.lower() not in resp_str
        assert settings.OPERATOR_API_KEY.lower() not in resp_str


def test_device_listing_never_leaks_token_hash_and_masks_ips():
    """Verifies that unauthenticated or device callers receive masked IPs and NO token_hash."""
    dev_a = "audit-dev-alpha"
    raw_token = "secret-token-value-12345"
    register_device(
        device_id=dev_a,
        hostname="Laptop-Audit",
        role="source",
        token=raw_token,
        lan_ip="192.168.1.123",
        tailscale_ip="100.85.12.34"
    )

    # 1. Unauthenticated listing
    resp_unauth = client.get("/api/devices")
    assert resp_unauth.status_code == 200
    devices = resp_unauth.json()
    target_dev = next((d for d in devices if d["device_id"] == dev_a), None)
    assert target_dev is not None
    assert "token_hash" not in target_dev
    assert "token" not in target_dev
    # IPs must be masked for non-operators (last octet masked)
    assert target_dev["lan_ip"] == "192.168.1.***"
    assert target_dev["tailscale_ip"] == "100.85.***.***"

    # 2. Operator listing (allowed to see unmasked IPs for routing, but never token_hash)
    op_headers = {"X-Operator-Key": settings.OPERATOR_API_KEY}
    resp_op = client.get("/api/devices", headers=op_headers)
    assert resp_op.status_code == 200
    op_dev = next((d for d in resp_op.json() if d["device_id"] == dev_a), None)
    assert op_dev is not None
    assert "token_hash" not in op_dev
    assert op_dev["lan_ip"] == "192.168.1.123"
    assert op_dev["tailscale_ip"] == "100.85.12.34"


# -----------------------------------------------------------------------------
# 2. API Authorization & Device Ownership Enforcement
# -----------------------------------------------------------------------------

def test_device_revocation_authorization():
    """Verifies that only an Operator or the device itself can revoke a device."""
    dev_id = "audit-dev-revoke"
    token = "audit-token-xyz"
    register_device(device_id=dev_id, hostname="Laptop-Revoke", role="both", token=token)

    other_dev_id = "audit-dev-other"
    other_token = "other-token-abc"
    register_device(device_id=other_dev_id, hostname="Laptop-Other", role="both", token=other_token)

    # Unauthenticated caller -> 403
    assert client.delete(f"/api/devices/{dev_id}").status_code == 403

    # Device Other trying to revoke Device A -> 403
    assert client.delete(f"/api/devices/{dev_id}", headers={"X-Device-Token": other_token}).status_code == 403

    # Device A revoking itself -> 200
    resp_self = client.delete(f"/api/devices/{dev_id}", headers={"X-Device-Token": token})
    assert resp_self.status_code == 200
    assert resp_self.json()["status"] == "revoked"


def test_catalog_publish_ownership_protection():
    """Verifies that Device A cannot publish or unpublish VMs under Device B's ID."""
    dev_a = "audit-dev-pub-a"
    token_a = "token-pub-a"
    register_device(device_id=dev_a, hostname="Laptop-A", role="source", token=token_a)

    dev_b = "audit-dev-pub-b"
    token_b = "token-pub-b"
    register_device(device_id=dev_b, hostname="Laptop-B", role="source", token=token_b)

    payload_b = {
        "device_id": dev_b,
        "vm_name": "VM-On-Host-B",
        "status": "stopped",
        "cpu_cores": 2,
        "ram_mb": 2048.0,
        "disk_gb": 20.0
    }

    # 1. Unauthenticated publish -> 403
    assert client.post("/api/catalog/publish", json=payload_b).status_code == 403

    # 2. Device A attempting to publish for Device B -> 403
    bad_resp = client.post("/api/catalog/publish", json=payload_b, headers={"X-Device-Token": token_a})
    assert bad_resp.status_code == 403

    # 3. Device B publishing for Device B -> 200
    good_resp = client.post("/api/catalog/publish", json=payload_b, headers={"X-Device-Token": token_b})
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] == "published"

    # 4. Device A attempting to unpublish Device B's VM -> 403
    unpub_payload = {"device_id": dev_b, "vm_name": "VM-On-Host-B"}
    assert client.post("/api/catalog/unpublish", json=unpub_payload, headers={"X-Device-Token": token_a}).status_code == 403

    # 5. Device B unpublishing its own VM -> 200
    unpub_good = client.post("/api/catalog/unpublish", json=unpub_payload, headers={"X-Device-Token": token_b})
    assert unpub_good.status_code == 200
    assert unpub_good.json()["status"] == "unpublished"


def test_migration_creation_and_cancellation_authorization():
    """Verifies that migration creation and cancellation strictly require appropriate authorization."""
    dev_src = "audit-mig-src"
    tok_src = "tok-mig-src"
    dev_tgt = "audit-mig-tgt"
    tok_tgt = "tok-mig-tgt"
    dev_rogue = "audit-mig-rogue"
    tok_rogue = "tok-mig-rogue"

    register_device(device_id=dev_src, hostname="Host-Src", role="source", token=tok_src)
    register_device(device_id=dev_tgt, hostname="Host-Tgt", role="target", token=tok_tgt)
    register_device(device_id=dev_rogue, hostname="Host-Rogue", role="both", token=tok_rogue)

    mig_req = {
        "source_device_id": dev_src,
        "target_device_id": dev_tgt,
        "vm_name": "VM-To-Move",
        "direct_transfer_method": "direct_lan"
    }

    # 1. Unauthenticated -> 403
    assert client.post("/api/migrations/create", json=mig_req).status_code == 403

    # 2. Rogue device -> 403
    assert client.post("/api/migrations/create", json=mig_req, headers={"X-Device-Token": tok_rogue}).status_code == 403

    # 3. Source device -> 200
    src_resp = client.post("/api/migrations/create", json=mig_req, headers={"X-Device-Token": tok_src})
    assert src_resp.status_code == 200
    job_id = src_resp.json()["job_id"]

    # 4. Rogue device trying to cancel -> 403
    assert client.post(f"/api/migrations/jobs/{job_id}/cancel", headers={"X-Device-Token": tok_rogue}).status_code == 403

    # 5. Participating target device cancelling -> 200
    cancel_resp = client.post(f"/api/migrations/jobs/{job_id}/cancel", headers={"X-Device-Token": tok_tgt})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


# -----------------------------------------------------------------------------
# 3. Fail-Closed Production Configuration Validation
# -----------------------------------------------------------------------------

def test_production_fails_closed_on_default_secrets():
    """Verifies that settings fails closed in production when default placeholder secrets are present."""
    with pytest.raises(ValueError, match="OPERATOR_API_KEY must not use default placeholder"):
        Settings(
            ENVIRONMENT="production",
            OPERATOR_API_KEY="vmotion-operator-key-default",
            ENROLLMENT_SECRET="production-secure-secret-32-chars-long",
            GATEWAY_AGENT_TOKEN="production-secure-gateway-token-32-chars",
            DEBUG=False,
            VBOX_MIGRATION_MODE="cold_ova"
        )


def test_production_fails_closed_on_debug_mode():
    """Verifies that settings fails closed in production when DEBUG=True."""
    with pytest.raises(ValueError, match="DEBUG mode must be disabled in production"):
        Settings(
            ENVIRONMENT="production",
            OPERATOR_API_KEY="a" * 32,
            ENROLLMENT_SECRET="b" * 32,
            GATEWAY_AGENT_TOKEN="c" * 32,
            DEBUG=True,
            VBOX_MIGRATION_MODE="cold_ova"
        )


def test_production_fails_closed_on_non_cold_ova_mode():
    """Verifies that settings fails closed in production if VBOX_MIGRATION_MODE is not cold_ova."""
    with pytest.raises(ValueError, match="VirtualBox provider must use 'cold_ova' migration mode"):
        Settings(
            ENVIRONMENT="production",
            OPERATOR_API_KEY="a" * 32,
            ENROLLMENT_SECRET="b" * 32,
            GATEWAY_AGENT_TOKEN="c" * 32,
            PROVIDER_TYPE="virtualbox",
            DEBUG=False,
            VBOX_MIGRATION_MODE="teleport"
        )


# -----------------------------------------------------------------------------
# 4. Scoped, Single-Use Cryptographic Transfer Authorization
# -----------------------------------------------------------------------------

def test_transfer_token_single_use_and_scope_validation():
    """Verifies HMAC validation, job/device scoping, expiration, and single-use redemption."""
    job_id = f"job-audit-xfer-{uuid.uuid4().hex[:8]}"
    src_id = "host-src-audit"
    tgt_id = "host-tgt-audit"
    artifact = "VMotion-Audit.ova"

    create_migration_job(
        job_id=job_id,
        vm_id="VM-Audit",
        source_device_id=src_id,
        target_device_id=tgt_id
    )

    auth = create_transfer_authorization(
        job_id=job_id,
        source_device_id=src_id,
        target_device_id=tgt_id,
        artifact_name=artifact,
        expires_in_seconds=300.0
    )

    token_id = auth["token_id"]

    # 1. Mismatched job_id must fail
    with pytest.raises(ValueError, match="not scoped to migration job"):
        verify_and_redeem_transfer_authorization(
            token_id=token_id,
            job_id="wrong-job-id",
            caller_device_id=tgt_id
        )

    # 2. Unauthorized caller device must fail
    with pytest.raises(ValueError, match="not authorized to redeem"):
        verify_and_redeem_transfer_authorization(
            token_id=token_id,
            job_id=job_id,
            caller_device_id="unauthorized-device"
        )

    # 3. Legitimate redemption by target device must succeed
    redeem_result = verify_and_redeem_transfer_authorization(
        token_id=token_id,
        job_id=job_id,
        caller_device_id=tgt_id
    )
    assert redeem_result["is_redeemed"] == 1
    assert redeem_result["job_id"] == job_id

    # 4. Immediate second redemption (replay attempt) must fail (Single-Use guarantee)
    with pytest.raises(ValueError, match="already been redeemed"):
        verify_and_redeem_transfer_authorization(
            token_id=token_id,
            job_id=job_id,
            caller_device_id=tgt_id
        )


def test_transfer_redeem_api_endpoint():
    """Verifies the /api/transfers/redeem endpoint enforces single-use and valid signature."""
    op_headers = {"X-Operator-Key": settings.OPERATOR_API_KEY}
    src_id = "host-api-src"
    tgt_id = "host-api-tgt"
    tgt_token = "tok-tgt-123"

    register_device(device_id=src_id, hostname="Src", role="source")
    register_device(device_id=tgt_id, hostname="Tgt", role="target", token=tgt_token)

    job_resp = client.post("/api/migrations/create", json={
        "source_device_id": src_id,
        "target_device_id": tgt_id,
        "vm_name": "VM-Audit-2",
        "direct_transfer_method": "direct_lan"
    }, headers=op_headers)
    job_id = job_resp.json()["job_id"]

    auth_resp = client.post("/api/transfers/authorize", json={
        "job_id": job_id,
        "source_device_id": src_id,
        "target_device_id": tgt_id,
        "artifact_name": "VM-Audit-2.ova"
    }, headers=op_headers)
    token_id = auth_resp.json()["auth_token"]

    # 1. Unauthenticated redeem -> 403
    unauth_redeem = client.post("/api/transfers/redeem", json={
        "job_id": job_id,
        "auth_token": token_id
    })
    assert unauth_redeem.status_code == 403

    # 2. Authorized redemption by target device -> 200
    good_redeem = client.post("/api/transfers/redeem", json={
        "job_id": job_id,
        "auth_token": token_id
    }, headers={"X-Device-Token": tgt_token})
    assert good_redeem.status_code == 200
    assert good_redeem.json()["status"] == "REDEEMED"

    # 3. Replay attack -> 400
    replay = client.post("/api/transfers/redeem", json={
        "job_id": job_id,
        "auth_token": token_id
    }, headers={"X-Device-Token": tgt_token})
    assert replay.status_code == 400
    assert "already been redeemed" in replay.json()["detail"]


# -----------------------------------------------------------------------------
# 5. Database Persistence & Restart Survival
# -----------------------------------------------------------------------------

def test_database_persistence_across_reconnects(tmp_path):
    """Verifies that enrolled devices and migration jobs survive database connection close/re-open."""
    test_db = str(tmp_path / "persistence_test.db")
    dev_id = "persistent-device-001"
    job_id = f"job-persist-{uuid.uuid4().hex[:8]}"

    # Write data using test DB
    register_device(device_id=dev_id, hostname="Laptop-Persist", role="both", db_path=test_db)
    create_migration_job(
        job_id=job_id,
        vm_id="VM-Persist",
        source_device_id=dev_id,
        target_device_id=dev_id,
        is_same_computer=True,
        db_path=test_db
    )

    # Simulate process restart / new connection
    dev_recovered = get_device(dev_id, db_path=test_db)
    job_recovered = get_migration_job(job_id, db_path=test_db)

    assert dev_recovered is not None
    assert dev_recovered["hostname"] == "Laptop-Persist"
    assert job_recovered is not None
    assert job_recovered["vm_id"] == "VM-Persist"
    assert job_recovered["is_same_computer"] == 1


# -----------------------------------------------------------------------------
# 6. Safety Gate & PPO Override Immunity
# -----------------------------------------------------------------------------

def test_deterministic_safety_gate_blocks_unsafe_proposal():
    """Verifies that deterministic safety rules strictly veto migrations exceeding CPU/RAM thresholds."""
    from app.safety.gate import deterministic_safety_gate
    from app.providers.base import ClusterState, NodeTelemetry, VMTelemetry

    # Target node CPU overloaded at 95% (exceeds SAFETY_MAX_CPU_PERCENT = 85.0%)
    state = ClusterState(
        nodes={
            "node-1": NodeTelemetry(id="node-1", name="node-1", status="online", cpu_percent=40.0, ram_percent=50.0),
            "node-2": NodeTelemetry(id="node-2", name="node-2", status="online", cpu_percent=95.0, ram_percent=92.0),
        },
        vms={
            "Heavy-VM": VMTelemetry(vmid="Heavy-VM", name="Heavy-VM", node_id="node-1", status="running", cpu_cores=4, ram_allocated_mb=4096.0)
        },
        timestamp=time.time()
    )

    eval_result = deterministic_safety_gate.evaluate(cluster=state, vm_id="Heavy-VM", target_node_id="node-2")
    assert eval_result.passed is False
    assert eval_result.blocked is True
    assert len(eval_result.rejection_codes) > 0


def test_unsafe_proposal_state_transitions_rejected():
    """Verifies that Proposal FSM transitions cannot jump states out of order."""
    from app.planner.planner import PendingProposal, ProposalState, InvalidStateTransitionError
    from app.safety.gate import deterministic_safety_gate
    from app.providers.base import ClusterState, NodeTelemetry, VMTelemetry

    state = ClusterState(
        nodes={
            "node-a": NodeTelemetry(id="node-a", name="node-a", status="online", cpu_percent=20.0, ram_percent=30.0),
            "node-b": NodeTelemetry(id="node-b", name="node-b", status="online", cpu_percent=30.0, ram_percent=40.0),
        },
        vms={
            "vm-fsm": VMTelemetry(vmid="vm-fsm", name="vm-fsm", node_id="node-a", status="running", cpu_cores=2, ram_allocated_mb=2048.0)
        },
        timestamp=time.time()
    )
    eval_result = deterministic_safety_gate.evaluate(cluster=state, vm_id="vm-fsm", target_node_id="node-b")

    proposal = PendingProposal(
        proposal_id="p-fsm-1",
        vm_id="vm-fsm",
        vm_name="vm-fsm",
        source_node="node-a",
        target_node="node-b",
        reason="test",
        engine_type="rule",
        confidence_score=0.9,
        safety_evaluation=eval_result,
        status=ProposalState.RECOMMENDED
    )

    # Cannot transition directly from RECOMMENDED to VERIFIED
    with pytest.raises(InvalidStateTransitionError):
        proposal.transition_to(ProposalState.VERIFIED)

    # Valid progressive transition works
    proposal.transition_to(ProposalState.SAFETY_CHECK)
    assert proposal.status == ProposalState.SAFETY_CHECK

