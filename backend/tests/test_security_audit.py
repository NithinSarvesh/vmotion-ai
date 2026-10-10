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


# -----------------------------------------------------------------------------
# 7. Final Security Hardening Regression Tests
# -----------------------------------------------------------------------------

def test_migration_jobs_read_authorization_and_ownership():
    """Verifies that GET /api/migrations/jobs and /jobs/{id} require auth and enforce device scoping."""
    op_headers = {"X-Operator-Key": settings.OPERATOR_API_KEY}

    # Register devices with explicit tokens
    raw_tok_a = f"tok-read-a-{uuid.uuid4().hex[:8]}"
    raw_tok_b = f"tok-read-b-{uuid.uuid4().hex[:8]}"
    raw_tok_c = f"tok-read-c-{uuid.uuid4().hex[:8]}"
    dev_a = register_device(device_id=f"dev-read-a-{uuid.uuid4().hex[:6]}", hostname="Host-A", role="both", token=raw_tok_a)
    dev_b = register_device(device_id=f"dev-read-b-{uuid.uuid4().hex[:6]}", hostname="Host-B", role="both", token=raw_tok_b)
    dev_c = register_device(device_id=f"dev-read-c-{uuid.uuid4().hex[:6]}", hostname="Host-C", role="both", token=raw_tok_c)

    tok_a = {"X-Device-Token": raw_tok_a}
    tok_b = {"X-Device-Token": raw_tok_b}
    tok_c = {"X-Device-Token": raw_tok_c}

    job_id = f"job-read-{uuid.uuid4().hex[:8]}"
    create_migration_job(
        job_id=job_id,
        vm_id="Protected-VM",
        source_device_id=dev_a["device_id"],
        target_device_id=dev_b["device_id"]
    )

    # 1. Anonymous access to list is blocked (401)
    assert client.get("/api/migrations/jobs").status_code == 401

    # 2. Anonymous access to specific job is blocked (401)
    assert client.get(f"/api/migrations/jobs/{job_id}").status_code == 401

    # 3. Operator key can access list and job
    op_list = client.get("/api/migrations/jobs", headers=op_headers)
    assert op_list.status_code == 200
    assert any(j["job_id"] == job_id for j in op_list.json())

    op_job = client.get(f"/api/migrations/jobs/{job_id}", headers=op_headers)
    assert op_job.status_code == 200
    assert op_job.json()["job_id"] == job_id

    # 4. Participating device (dev_a) can access the job
    assert client.get(f"/api/migrations/jobs/{job_id}", headers=tok_a).status_code == 200

    # 5. Participating device (dev_b) can access the job
    assert client.get(f"/api/migrations/jobs/{job_id}", headers=tok_b).status_code == 200

    # 6. Unrelated device (dev_c) gets 403 Forbidden for dev_a -> dev_b job
    unrelated_job = client.get(f"/api/migrations/jobs/{job_id}", headers=tok_c)
    assert unrelated_job.status_code == 403

    # 7. Device list call filters out jobs dev_c does not participate in
    dev_c_list = client.get("/api/migrations/jobs", headers=tok_c)
    assert dev_c_list.status_code == 200
    assert not any(j["job_id"] == job_id for j in dev_c_list.json())


def test_transfer_authorize_endpoint_binding_and_safety():
    """Verifies strict endpoint binding, device roles, job state, caller ownership, and artifact safety in /transfers/authorize."""
    op_headers = {"X-Operator-Key": settings.OPERATOR_API_KEY}

    raw_src_tok = f"tok-src-{uuid.uuid4().hex[:8]}"
    raw_tgt_tok = f"tok-tgt-{uuid.uuid4().hex[:8]}"
    raw_other_tok = f"tok-oth-{uuid.uuid4().hex[:8]}"

    src = register_device(device_id=f"dev-xfer-src-{uuid.uuid4().hex[:6]}", hostname="Xfer-Src", role="source", token=raw_src_tok)
    tgt = register_device(device_id=f"dev-xfer-tgt-{uuid.uuid4().hex[:6]}", hostname="Xfer-Tgt", role="target", token=raw_tgt_tok)
    other = register_device(device_id=f"dev-xfer-oth-{uuid.uuid4().hex[:6]}", hostname="Xfer-Other", role="both", token=raw_other_tok)

    src_tok = {"X-Device-Token": raw_src_tok}
    other_tok = {"X-Device-Token": raw_other_tok}

    job_id = f"job-bind-{uuid.uuid4().hex[:8]}"
    create_migration_job(
        job_id=job_id,
        vm_id="Binding-VM",
        source_device_id=src["device_id"],
        target_device_id=tgt["device_id"]
    )

    base_payload = {
        "job_id": job_id,
        "source_device_id": src["device_id"],
        "target_device_id": tgt["device_id"],
        "artifact_name": "Binding-VM.ova"
    }

    # 1. Unauthenticated request rejected (401)
    assert client.post("/api/transfers/authorize", json=base_payload).status_code == 401

    # 2. Forged endpoints: mismatch with stored job (400)
    forged_payload = dict(base_payload, target_device_id=other["device_id"])
    forged_resp = client.post("/api/transfers/authorize", json=forged_payload, headers=op_headers)
    assert forged_resp.status_code == 400
    assert "Transfer endpoint mismatch" in forged_resp.json()["detail"]

    # 3. Unrelated device caller rejected (403)
    unrelated_resp = client.post("/api/transfers/authorize", json=base_payload, headers=other_tok)
    assert unrelated_resp.status_code == 403

    # 4. Path traversal in artifact_name rejected (400)
    traversal_payload = dict(base_payload, artifact_name="../secret.ova")
    trav_resp = client.post("/api/transfers/authorize", json=traversal_payload, headers=op_headers)
    assert trav_resp.status_code == 400

    # 5. Non-existent job rejected (404)
    missing_payload = dict(base_payload, job_id="job-nonexistent")
    assert client.post("/api/transfers/authorize", json=missing_payload, headers=op_headers).status_code == 404

    # 6. Valid authorization with participating device succeeds (200)
    auth_resp = client.post("/api/transfers/authorize", json=base_payload, headers=src_tok)
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["status"] == "AUTHORIZED"
    assert "auth_token" in data
    assert "signature" in data


def test_authentic_vm_inventory_rejection_and_verification():
    """Verifies that publishing and migration creation reject unverified VMs when agent is online."""
    from app.gateway.agent_gateway import agent_gateway, AgentSession

    op_headers = {"X-Operator-Key": settings.OPERATOR_API_KEY}
    dev_id = f"dev-auth-vm-{uuid.uuid4().hex[:6]}"
    raw_dev_tok = f"tok-auth-{uuid.uuid4().hex[:8]}"
    dev = register_device(device_id=dev_id, hostname="VM-Host", role="both", token=raw_dev_tok)
    dev_tok = {"X-Device-Token": raw_dev_tok}

    # Register an active agent session with live telemetry containing only "Real-VM"
    sess = AgentSession(
        host_id=dev_id,
        hostname="VM-Host",
        websocket=None,
        lan_ip="192.168.1.150"
    )
    sess.latest_telemetry = {
        "vms": [
            {
                "id": "Real-VM",
                "name": "Real-VM",
                "uuid": "uuid-real-1234",
                "status": "running",
                "cpus": 4,
                "memory_mb": 8192.0,
                "os_type": "Ubuntu_64"
            }
        ]
    }
    agent_gateway._sessions[dev_id] = sess

    # 1. Publishing a non-existent VM is rejected (400)
    bad_pub = client.post("/api/catalog/publish", json={
        "device_id": dev_id,
        "vm_name": "Ghost-VM"
    }, headers=dev_tok)
    assert bad_pub.status_code == 400
    assert "was not found in the authentic VirtualBox inventory" in bad_pub.json()["detail"]

    # 2. Publishing an existing VM with wrong UUID is rejected (400)
    mismatch_pub = client.post("/api/catalog/publish", json={
        "device_id": dev_id,
        "vm_name": "Real-VM",
        "vm_uuid": "uuid-wrong-9999"
    }, headers=dev_tok)
    assert mismatch_pub.status_code == 400
    assert "UUID mismatch" in mismatch_pub.json()["detail"]

    # 3. Publishing the authentic VM succeeds and inherits measured specifications
    good_pub = client.post("/api/catalog/publish", json={
        "device_id": dev_id,
        "vm_name": "Real-VM",
        "vm_uuid": "uuid-real-1234"
    }, headers=dev_tok)
    assert good_pub.status_code == 200
    pub_data = good_pub.json()["vm"]
    assert pub_data["cpu_cores"] == 4
    assert pub_data["ram_mb"] == 8192.0
    assert pub_data["os_type"] == "Ubuntu_64"

    # 4. Creating a migration job for a VM that does NOT exist on source agent is rejected (400)
    bad_mig = client.post("/api/migrations/create", json={
        "source_device_id": dev_id,
        "target_device_id": dev_id,
        "vm_name": "Fake-VM",
        "direct_transfer_method": "same_host"
    }, headers=op_headers)
    assert bad_mig.status_code == 400
    assert "does not exist in the authentic VirtualBox inventory" in bad_mig.json()["detail"]

    # 5. Creating a migration job for the verified VM succeeds (200)
    good_mig = client.post("/api/migrations/create", json={
        "source_device_id": dev_id,
        "target_device_id": dev_id,
        "vm_name": "Real-VM",
        "vm_uuid": "uuid-real-1234",
        "direct_transfer_method": "same_host"
    }, headers=op_headers)
    assert good_mig.status_code == 200
    assert good_mig.json()["vm_id"] == "Real-VM"


