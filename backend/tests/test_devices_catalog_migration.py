"""
Unit & Integration Tests for Device Enrollment, VM Catalog Publishing,
Migration Job FSM Tracking, Agent Download, and Transfer Authorization.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import settings
from app.db.database import (
    register_device,
    get_device,
    list_devices,
    revoke_device,
    publish_vm,
    unpublish_vm,
    list_published_vms,
    create_migration_job,
    get_migration_job,
    update_migration_job
)

client = TestClient(app)


def test_device_enrollment_and_lifecycle():
    """Verifies physical device enrollment, listing, and revocation."""
    # 1. Reject invalid enrollment secret
    bad_resp = client.post("/api/devices/enroll", json={
        "hostname": "Laptop-Alpha",
        "role": "source",
        "enrollment_secret": "wrong-secret-key"
    })
    assert bad_resp.status_code == 401

    # 2. Accept valid enrollment secret
    good_resp = client.post("/api/devices/enroll", json={
        "hostname": "Laptop-Alpha",
        "role": "source",
        "owner_name": "Test Engineer",
        "enrollment_secret": settings.ENROLLMENT_SECRET,
        "vbox_version": "7.2.16",
        "lan_ip": "192.168.1.150"
    })
    assert good_resp.status_code == 200
    data = good_resp.json()
    assert data["status"] == "enrolled"
    assert "device_id" in data
    assert "token" in data
    assert data["role"] == "source"
    dev_id = data["device_id"]

    # 3. List devices
    list_resp = client.get("/api/devices")
    assert list_resp.status_code == 200
    devs = list_resp.json()
    assert any(d["device_id"] == dev_id for d in devs)

    # 4. Revoke device
    del_resp = client.delete(f"/api/devices/{dev_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "revoked"


def test_vm_catalog_publishing():
    """Verifies VM catalog publish, list, and unpublish operations."""
    # Setup test device
    dev_id = "test-host-cat"
    register_device(device_id=dev_id, hostname="Catalog-Host", role="source")

    # 1. Publish VM
    pub_resp = client.post("/api/catalog/publish", json={
        "device_id": dev_id,
        "vm_name": "Test-Ubuntu-VM",
        "status": "stopped",
        "cpu_cores": 4,
        "ram_mb": 4096.0,
        "disk_gb": 30.0,
        "os_type": "Ubuntu_64"
    })
    assert pub_resp.status_code == 200
    data = pub_resp.json()
    assert data["status"] == "published"
    assert data["vm"]["name"] == "Test-Ubuntu-VM"

    # 2. List published VMs
    list_resp = client.get("/api/catalog/vms")
    assert list_resp.status_code == 200
    catalog = list_resp.json()
    assert any(v["name"] == "Test-Ubuntu-VM" for v in catalog)

    # 3. Unpublish VM
    unpub_resp = client.post("/api/catalog/unpublish", json={
        "device_id": dev_id,
        "vm_name": "Test-Ubuntu-VM"
    })
    assert unpub_resp.status_code == 200
    assert unpub_resp.json()["status"] == "unpublished"


def test_migration_job_creation_and_tracking():
    """Verifies persistent migration job creation, same-computer detection, and retrieval."""
    # 1. Same-computer migration job creation
    same_resp = client.post("/api/migrations/create", json={
        "source_device_id": "vbox-host-local",
        "target_device_id": "vbox-host-local",
        "vm_name": "VMotion-Demo",
        "direct_transfer_method": "same_host",
        "auto_start_target": True
    })
    assert same_resp.status_code == 200
    same_job = same_resp.json()
    assert same_job["is_same_computer"] == 1 or same_job["is_same_computer"] is True
    job_id = same_job["job_id"]

    # 2. Retrieve job status
    get_resp = client.get(f"/api/migrations/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["job_id"] == job_id

    # 3. Cancel job
    cancel_resp = client.post(f"/api/migrations/jobs/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 4. Verify cancelled state
    check_resp = client.get(f"/api/migrations/jobs/{job_id}")
    assert check_resp.json()["state"] == "FAILED"
    assert check_resp.json()["stage"] == "CANCELLED"


def test_agent_download_endpoint():
    """Verifies that the /api/agent/download endpoint serves the executable or returns instructions."""
    resp = client.get("/api/agent/download")
    assert resp.status_code == 200
    # If binary exists, Content-Type is application/octet-stream; otherwise JSON
    ct = resp.headers.get("content-type", "")
    assert "application/octet-stream" in ct or "application/json" in ct


def test_transfer_authorization():
    """Verifies cryptographic one-time transfer token generation."""
    resp = client.post("/api/transfers/authorize", json={
        "job_id": "job-abc12345",
        "source_device_id": "dev-src",
        "target_device_id": "dev-tgt",
        "artifact_name": "VMotion-Migration-abc12345.ova"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "AUTHORIZED"
    assert "auth_token" in data
    assert len(data["auth_token"]) == 64
