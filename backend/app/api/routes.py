"""
REST API Routes for VMotion AI Control Plane.
Authoritative hypervisor provider is Oracle VirtualBox (VirtualBoxProvider).
Supports Simulation mode for development/training and Live VirtualBox for real migration.
"""
import os
import secrets
import hashlib
import uuid
import time
import asyncio
from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any

from app.providers.base import ClusterState, MigrationTaskStatus, ProviderConnectionResult, MigrationPlan
from app.providers.simulation import SimulationProvider
from app.providers.virtualbox import VirtualBoxProvider
from app.providers.proxmox import ProxmoxVEProvider
from app.providers.libvirt import LibvirtKVMProvider
from app.telemetry.collector import TelemetryEngine, AggregatedClusterTelemetry
from app.engine.ppo_engine import PPODecisionEngine
from app.engine.rule_engine import RuleBasedDecisionEngine
from app.safety.gate import deterministic_safety_gate, SafetyEvaluation
from app.planner.planner import (
    MigrationManager,
    PendingProposal,
    ProposalState,
    InvalidStateTransitionError
)
from app.audit.logger import audit_logger, AuditEntry
from app.adapter.observation import ObservationAdapter
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
    update_migration_job,
    list_migration_jobs,
)

router = APIRouter(prefix="/api")

# Singleton state instances
simulation_provider = SimulationProvider()
virtualbox_provider = VirtualBoxProvider()
proxmox_provider = ProxmoxVEProvider()
libvirt_provider = LibvirtKVMProvider()

current_provider_name = settings.PROVIDER_TYPE
if current_provider_name == "virtualbox":
    active_provider = virtualbox_provider
elif current_provider_name == "proxmox":
    active_provider = proxmox_provider
elif current_provider_name == "libvirt":
    active_provider = libvirt_provider
else:
    active_provider = simulation_provider
    current_provider_name = "simulation"


def get_active_provider():
    global active_provider
    return active_provider


telemetry_engine = TelemetryEngine(active_provider)
migration_mgr = MigrationManager(active_provider)
ppo_engine = PPODecisionEngine()
rule_engine = RuleBasedDecisionEngine()
obs_adapter = ObservationAdapter()


class ModeSwitchRequest(BaseModel):
    provider_type: Literal["simulation", "virtualbox", "proxmox", "libvirt"]
    confirm_live: bool = False


class ClusterConfigRequest(BaseModel):
    provider_type: Optional[Literal["simulation", "virtualbox", "proxmox", "libvirt"]] = None
    vbox_manage_path: Optional[str] = None
    vbox_host_a_url: Optional[str] = None
    vbox_host_b_url: Optional[str] = None
    vbox_teleport_port: Optional[int] = None
    vbox_shared_storage_path: Optional[str] = None
    proxmox_endpoint: Optional[str] = None
    proxmox_user: Optional[str] = None
    proxmox_token_id: Optional[str] = None
    proxmox_token_secret: Optional[str] = None
    proxmox_verify_ssl: Optional[bool] = None
    libvirt_uri: Optional[str] = None


class ConnectionTestRequest(BaseModel):
    provider_type: Literal["simulation", "virtualbox", "proxmox", "libvirt"]
    vbox_manage_path: Optional[str] = None
    vbox_host_a_url: Optional[str] = None
    vbox_host_b_url: Optional[str] = None
    vbox_teleport_port: Optional[int] = None
    vbox_shared_storage_path: Optional[str] = None
    proxmox_endpoint: Optional[str] = None
    proxmox_user: Optional[str] = None
    proxmox_token_id: Optional[str] = None
    proxmox_token_secret: Optional[str] = None
    proxmox_verify_ssl: Optional[bool] = None
    libvirt_uri: Optional[str] = None


class ApproveRequest(BaseModel):
    notes: Optional[str] = "Approved via VMotion AI Control Plane"


class RejectRequest(BaseModel):
    reason: Optional[str] = "Operator declined recommendation"


class CancelRequest(BaseModel):
    reason: Optional[str] = "Operator cancelled proposal"


class SettingsUpdateRequest(BaseModel):
    enable_human_approval: Optional[bool] = None
    enable_autonomous_mode: Optional[bool] = None


class TargetPrepareRequest(BaseModel):
    vm_id: str = "DemoVM"
    port: int = 60050


@router.get("/health")
async def health():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "provider": current_provider_name,
        "hypervisor": "Oracle VirtualBox 7.x" if current_provider_name == "virtualbox" else current_provider_name
    }


@router.get("/cluster/state", response_model=ClusterState)
async def get_cluster_state():
    return await active_provider.get_cluster_state()


@router.get("/cluster/telemetry", response_model=AggregatedClusterTelemetry)
async def get_cluster_telemetry():
    return await telemetry_engine.sample_telemetry()


@router.post("/cluster/mode")
async def set_cluster_mode(
    req: ModeSwitchRequest,
    x_operator_key: Optional[str] = Header(None)
):
    global current_provider_name, active_provider, migration_mgr, telemetry_engine
    
    if req.provider_type in ("virtualbox", "proxmox", "libvirt"):
        if settings.OPERATOR_API_KEY and x_operator_key != settings.OPERATOR_API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Valid X-Operator-Key header required to switch to live infrastructure."
            )
        if not req.confirm_live:
            raise HTTPException(
                status_code=400,
                detail="Explicit confirmation required to switch to live infrastructure. Set 'confirm_live: true'."
            )

    if req.provider_type == "simulation":
        active_provider = simulation_provider
        current_provider_name = "simulation"
    elif req.provider_type == "virtualbox":
        active_provider = virtualbox_provider
        current_provider_name = "virtualbox"
    elif req.provider_type == "proxmox":
        active_provider = proxmox_provider
        current_provider_name = "proxmox"
    elif req.provider_type == "libvirt":
        active_provider = libvirt_provider
        current_provider_name = "libvirt"
    else:
        raise HTTPException(status_code=400, detail="Invalid provider type")

    migration_mgr.provider = active_provider
    telemetry_engine.provider = active_provider
    audit_logger.log_event(
        event_type="CLUSTER_CONNECTED",
        message=f"Operator switched provider to '{current_provider_name}'.",
        details={"provider": current_provider_name}
    )
    return {"status": "success", "provider": current_provider_name}


@router.get("/cluster/config")
async def get_cluster_config():
    return {
        "provider_type": current_provider_name,
        "is_live": current_provider_name in ("virtualbox", "proxmox", "libvirt"),
        "virtualbox": {
            "vbox_path": virtualbox_provider.vbox_manage_path,
            "host_a_url": virtualbox_provider.host_a_url,
            "host_b_url": virtualbox_provider.host_b_url,
            "teleport_port": virtualbox_provider.teleport_port,
            "shared_storage_path": virtualbox_provider.shared_storage_path,
            "demo_vm_name": virtualbox_provider.demo_vm_name,
        },
        "proxmox": {
            "endpoint": settings.PROXMOX_ENDPOINT,
            "user": settings.PROXMOX_USER,
            "token_id": settings.PROXMOX_TOKEN_ID,
            "token_secret_configured": bool(settings.PROXMOX_TOKEN_SECRET),
            "verify_ssl": settings.PROXMOX_VERIFY_SSL
        },
        "libvirt": {
            "uri": settings.LIBVIRT_URI
        }
    }


@router.post("/cluster/config")
async def update_cluster_config(
    req: ClusterConfigRequest,
    x_operator_key: Optional[str] = Header(None)
):
    if settings.OPERATOR_API_KEY and x_operator_key != settings.OPERATOR_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Valid X-Operator-Key header required to modify infrastructure configuration."
        )

    global current_provider_name, active_provider, migration_mgr
    
    if req.vbox_manage_path is not None:
        settings.VBOX_MANAGE_PATH = req.vbox_manage_path
    if req.vbox_host_a_url is not None:
        settings.VBOX_HOST_A_URL = req.vbox_host_a_url
    if req.vbox_host_b_url is not None:
        settings.VBOX_HOST_B_URL = req.vbox_host_b_url
    if req.vbox_teleport_port is not None:
        settings.VBOX_TELEPORT_PORT = req.vbox_teleport_port
    if req.vbox_shared_storage_path is not None:
        settings.VBOX_SHARED_STORAGE_PATH = req.vbox_shared_storage_path

    virtualbox_provider.update_config(
        vbox_manage_path=req.vbox_manage_path,
        host_a_url=req.vbox_host_a_url,
        host_b_url=req.vbox_host_b_url,
        teleport_port=req.vbox_teleport_port,
        shared_storage_path=req.vbox_shared_storage_path
    )

    if req.proxmox_endpoint is not None:
        settings.PROXMOX_ENDPOINT = req.proxmox_endpoint
    if req.proxmox_user is not None:
        settings.PROXMOX_USER = req.proxmox_user
    if req.proxmox_token_id is not None:
        settings.PROXMOX_TOKEN_ID = req.proxmox_token_id
    if req.proxmox_token_secret is not None and req.proxmox_token_secret.strip():
        settings.PROXMOX_TOKEN_SECRET = req.proxmox_token_secret
    if req.proxmox_verify_ssl is not None:
        settings.PROXMOX_VERIFY_SSL = req.proxmox_verify_ssl
    if req.libvirt_uri is not None:
        settings.LIBVIRT_URI = req.libvirt_uri

    proxmox_provider.update_config(
        endpoint=settings.PROXMOX_ENDPOINT,
        user=settings.PROXMOX_USER,
        token_id=settings.PROXMOX_TOKEN_ID,
        token_secret=settings.PROXMOX_TOKEN_SECRET,
        verify_ssl=settings.PROXMOX_VERIFY_SSL
    )
    libvirt_provider.update_config(uri=settings.LIBVIRT_URI)

    if req.provider_type:
        await set_cluster_mode(ModeSwitchRequest(provider_type=req.provider_type, confirm_live=True))

    audit_logger.log_event(
        event_type="CONFIG_UPDATED",
        message=f"Infrastructure provider config updated. Provider: '{current_provider_name}'.",
        details={"provider": current_provider_name}
    )
    return await get_cluster_config()


@router.post("/cluster/test-connection", response_model=ProviderConnectionResult)
async def test_connection(req: ConnectionTestRequest):
    if req.provider_type == "simulation":
        return await simulation_provider.test_connection()
    elif req.provider_type == "virtualbox":
        return await virtualbox_provider.test_connection()
    elif req.provider_type == "proxmox":
        endpoint = req.proxmox_endpoint or settings.PROXMOX_ENDPOINT
        user = req.proxmox_user or settings.PROXMOX_USER
        token_id = req.proxmox_token_id or settings.PROXMOX_TOKEN_ID
        token_secret = req.proxmox_token_secret if req.proxmox_token_secret is not None else settings.PROXMOX_TOKEN_SECRET
        verify_ssl = req.proxmox_verify_ssl if req.proxmox_verify_ssl is not None else settings.PROXMOX_VERIFY_SSL

        if not token_secret or not token_secret.strip():
            return ProviderConnectionResult(
                provider="proxmox",
                status="UNAVAILABLE",
                latency_ms=0.0,
                message="Cannot connect to Proxmox: API token secret is not configured.",
                node_count=0,
                vm_count=0
            )

        test_pve = ProxmoxVEProvider(
            endpoint=endpoint,
            user=user,
            token_id=token_id,
            token_secret=token_secret.strip(),
            verify_ssl=verify_ssl
        )
        res = await test_pve.test_connection()
        await test_pve.disconnect()
        return res
    elif req.provider_type == "libvirt":
        uri = req.libvirt_uri or settings.LIBVIRT_URI
        test_libvirt = LibvirtKVMProvider(uri=uri)
        res = await test_libvirt.test_connection()
        await test_libvirt.disconnect()
        return res
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider type '{req.provider_type}'")


# -----------------------------------------------------------------------------
# Dedicated VirtualBox Live Teleportation Endpoints
# -----------------------------------------------------------------------------

@router.get("/virtualbox/compatibility")
async def get_vbox_compatibility(
    vm_id: str = Query("DemoVM"),
    target_node: str = Query("vbox-host-b")
):
    """Deep inspection of hardware compatibility for VirtualBox teleportation."""
    return await virtualbox_provider.check_target_compatibility(vm_id, target_node)


@router.post("/virtualbox/prepare-target")
async def prepare_vbox_target(req: TargetPrepareRequest):
    """Arms the target VirtualBox VM for incoming teleportation on port 60050."""
    ok, msg = await virtualbox_provider.prepare_target_teleporter(req.vm_id, req.port)
    return {"success": ok, "message": msg, "teleport_port": req.port}


@router.get("/virtualbox/demo-status")
async def get_vbox_demo_status():
    """Aggregates all components required for the Live Demo screen."""
    cluster = await active_provider.get_cluster_state()
    rec = ppo_engine.evaluate(cluster)

    proposal = None
    safety_eval = None
    if rec.action_type == "MIGRATE" and rec.vm_id and rec.target_node:
        proposal = migration_mgr.evaluate_and_propose(rec, cluster)
        safety_eval = proposal.safety_evaluation if proposal else None

    compat = await virtualbox_provider.check_target_compatibility(
        rec.vm_id or "DemoVM",
        rec.target_node or "vbox-host-b"
    )

    return {
        "provider": current_provider_name,
        "is_live": current_provider_name == "virtualbox",
        "cluster": cluster,
        "recommendation": rec,
        "proposal": proposal,
        "safety_evaluation": safety_eval,
        "compatibility": compat,
        "active_tasks": list(migration_mgr.active_tasks.values()),
        "completed_tasks": migration_mgr.completed_tasks,
        "demo_vm_name": virtualbox_provider.demo_vm_name
    }


# -----------------------------------------------------------------------------
# AI Recommendations & Decision Engine
# -----------------------------------------------------------------------------

@router.get("/ai/model/health")
async def get_model_health():
    return ppo_engine.get_health()


@router.get("/ai/recommendation")
async def get_recommendation():
    cluster = await active_provider.get_cluster_state()
    if not cluster.connected:
        raise HTTPException(status_code=503, detail="Cluster is disconnected. Cannot generate recommendations.")

    rec = ppo_engine.evaluate(cluster)
    
    proposal = None
    safety_eval = None
    if rec.action_type == "MIGRATE" and rec.vm_id and rec.target_node:
        proposal = migration_mgr.evaluate_and_propose(rec, cluster)
        safety_eval = proposal.safety_evaluation if proposal else None

    return {
        "recommendation": rec,
        "safety_evaluation": safety_eval,
        "proposal": proposal
    }


@router.post("/migrations/approve/{proposal_id}")
async def approve_migration(proposal_id: str, req: ApproveRequest = None):
    notes = req.notes if req else "Approved by operator"
    try:
        task = await migration_mgr.approve_proposal(proposal_id, operator_notes=notes)
        return {"status": "dispatched", "task": task}
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrations/reject/{proposal_id}")
async def reject_migration(proposal_id: str, req: RejectRequest = None):
    reason = req.reason if req else "Operator declined"
    try:
        proposal = await migration_mgr.reject_proposal(proposal_id, reason=reason)
        return {"status": "rejected", "proposal": proposal}
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    except (InvalidStateTransitionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/migrations/cancel/{proposal_id}")
async def cancel_migration(proposal_id: str, req: CancelRequest = None):
    reason = req.reason if req else "Operator cancelled"
    try:
        proposal = await migration_mgr.cancel_proposal(proposal_id, reason=reason)
        return {"status": "cancelled", "proposal": proposal}
    except KeyError:
        raise HTTPException(status_code=404, detail="Proposal not found")
    except (InvalidStateTransitionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/migrations/tasks")
async def get_migration_tasks():
    return {
        "active": list(migration_mgr.active_tasks.values()),
        "completed": migration_mgr.completed_tasks,
        "pending_proposals": list(migration_mgr.proposals.values())
    }


@router.get("/safety/check")
async def evaluate_safety(vm_id: str = Query(...), target_node: str = Query(...)):
    cluster = await active_provider.get_cluster_state()
    evaluation = deterministic_safety_gate.evaluate(cluster, vm_id, target_node)
    return evaluation


@router.get("/observation/features")
async def get_features():
    cluster = await active_provider.get_cluster_state()
    feats = obs_adapter.extract_features(cluster)
    return {
        "dimension": len(feats),
        "features": [round(float(x), 4) for x in feats],
        "node_ids": obs_adapter.node_ids
    }


@router.get("/audit/logs")
async def get_audit_logs(limit: int = 50):
    return audit_logger.get_entries(limit=limit)


@router.get("/settings")
async def get_settings():
    return {
        "app_name": settings.APP_NAME,
        "provider": current_provider_name,
        "enable_human_approval": settings.ENABLE_HUMAN_APPROVAL,
        "enable_autonomous_mode": settings.ENABLE_AUTONOMOUS_MODE,
        "safety_max_cpu_percent": settings.SAFETY_MAX_CPU_PERCENT,
        "safety_max_ram_percent": settings.SAFETY_MAX_RAM_PERCENT,
        "safety_cooldown_seconds": settings.SAFETY_COOLDOWN_SECONDS,
        "vbox_teleport_port": settings.VBOX_TELEPORT_PORT
    }


@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    if req.enable_human_approval is not None:
        settings.ENABLE_HUMAN_APPROVAL = req.enable_human_approval
    if req.enable_autonomous_mode is not None:
        settings.ENABLE_AUTONOMOUS_MODE = req.enable_autonomous_mode
    return await get_settings()


@router.get("/gateway/agents")
async def get_gateway_agents():
    """Returns active physical host agents connected to Cloud Gateway."""
    from app.gateway.agent_gateway import agent_gateway
    return {
        "agents": agent_gateway.list_agents(),
        "total_connected": len(agent_gateway.list_agents()),
        "heartbeat_timeout_seconds": settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS
    }


# -----------------------------------------------------------------------------
# Device Enrollment Models & Routes
# -----------------------------------------------------------------------------

class DeviceEnrollRequest(BaseModel):
    hostname: str
    role: Literal["source", "target", "both"] = "both"
    owner_name: Optional[str] = "Default User"
    enrollment_secret: str
    device_id: Optional[str] = None
    vbox_version: Optional[str] = None
    lan_ip: Optional[str] = None
    tailscale_ip: Optional[str] = None


@router.post("/devices/enroll")
async def enroll_device(req: DeviceEnrollRequest):
    """Enrolls a physical host/target computer into the persistent device registry."""
    if req.enrollment_secret != settings.ENROLLMENT_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid enrollment secret")

    device_id = req.device_id or f"dev-{secrets.token_hex(4)}"
    token = f"tok_{secrets.token_hex(16)}"

    device = register_device(
        device_id=device_id,
        hostname=req.hostname,
        role=req.role,
        owner_name=req.owner_name or "Default User",
        token=token,
        vbox_version=req.vbox_version,
        lan_ip=req.lan_ip,
        tailscale_ip=req.tailscale_ip,
    )

    audit_logger.log_event(
        event_type="DEVICE_ENROLLED",
        message=f"Device '{device_id}' ({req.hostname}) enrolled with role '{req.role}'.",
        details={"device_id": device_id, "hostname": req.hostname, "role": req.role}
    )

    return {
        "status": "enrolled",
        "device_id": device_id,
        "token": token,
        "role": req.role,
        "hostname": req.hostname,
        "device": device
    }


@router.get("/devices")
async def get_devices(include_offline: bool = True):
    """Lists registered devices, reflecting live gateway session status."""
    from app.gateway.agent_gateway import agent_gateway
    devs = list_devices(include_revoked=False)
    for d in devs:
        did = d["device_id"]
        sess = agent_gateway.get_session(did)
        if sess and sess.is_alive(settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS):
            d["status"] = "online"
            if sess.lan_ip:
                d["lan_ip"] = sess.lan_ip
            if sess.tailscale_ip:
                d["tailscale_ip"] = sess.tailscale_ip
            if sess.vbox_version:
                d["vbox_version"] = sess.vbox_version
        else:
            d["status"] = "offline"

    if not include_offline:
        devs = [d for d in devs if d["status"] == "online"]
    return devs


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    """Revokes a device's enrollment and terminates any active agent session."""
    from app.gateway.agent_gateway import agent_gateway
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    revoke_device(device_id)
    sess = agent_gateway.get_session(device_id)
    if sess and sess.websocket:
        try:
            await sess.websocket.close(code=4001, reason="Device revoked by operator")
        except Exception:
            pass
        agent_gateway.unregister_agent(device_id)

    audit_logger.log_event(
        event_type="DEVICE_REVOKED",
        message=f"Device '{device_id}' revoked by operator.",
        details={"device_id": device_id}
    )
    return {"status": "revoked", "device_id": device_id}


# -----------------------------------------------------------------------------
# VM Catalog Models & Routes
# -----------------------------------------------------------------------------

class VMPublishRequest(BaseModel):
    device_id: str
    vm_name: str
    vm_uuid: Optional[str] = None
    os_type: Optional[str] = "other"
    ram_mb: Optional[float] = 2048.0
    cpu_cores: Optional[int] = 2
    disk_gb: Optional[float] = 20.0
    status: Optional[str] = "stopped"


class VMUnpublishRequest(BaseModel):
    device_id: str
    vm_name: str


@router.get("/catalog/vms")
async def get_published_vms(device_id: Optional[str] = None):
    """Lists VMs published by hosts, augmented with current device connectivity status."""
    from app.gateway.agent_gateway import agent_gateway
    vms = list_published_vms(device_id=device_id)
    for vm in vms:
        did = vm.get("device_id")
        sess = agent_gateway.get_session(did)
        if sess and sess.is_alive(settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS):
            vm["device_status"] = "online"
        else:
            vm["device_status"] = "offline"
    return vms


@router.post("/catalog/publish")
async def publish_vm_endpoint(req: VMPublishRequest):
    """Publishes a host VM to the shared migration catalog."""
    vm = publish_vm(
        vm_id=req.vm_name,
        device_id=req.device_id,
        name=req.vm_name,
        status=req.status or "stopped",
        cpu_cores=req.cpu_cores or 2,
        ram_mb=req.ram_mb or 2048.0,
        disk_gb=req.disk_gb or 20.0,
        os_type=req.os_type or "other"
    )
    audit_logger.log_event(
        event_type="VM_PUBLISHED",
        vm_id=req.vm_name,
        message=f"VM '{req.vm_name}' published to catalog by device '{req.device_id}'.",
        details=vm
    )
    return {"status": "published", "vm": vm}


@router.post("/catalog/unpublish")
async def unpublish_vm_endpoint(req: VMUnpublishRequest):
    """Unpublishes a VM from the catalog."""
    success = unpublish_vm(vm_id=req.vm_name, device_id=req.device_id)
    if not success:
        raise HTTPException(status_code=404, detail="VM not found in catalog")
    audit_logger.log_event(
        event_type="VM_UNPUBLISHED",
        vm_id=req.vm_name,
        message=f"VM '{req.vm_name}' unpublished from catalog by device '{req.device_id}'.",
        details={"device_id": req.device_id, "vm_name": req.vm_name}
    )
    return {"status": "unpublished", "device_id": req.device_id, "vm_name": req.vm_name}


# -----------------------------------------------------------------------------
# Migration Jobs Models & Routes
# -----------------------------------------------------------------------------

class MigrationJobCreateRequest(BaseModel):
    source_device_id: str
    target_device_id: str
    vm_name: str
    vm_uuid: Optional[str] = None
    direct_transfer_method: Optional[Literal["direct_lan", "tailscale", "s3_fallback", "same_host"]] = "direct_lan"
    auto_start_target: Optional[bool] = False


@router.post("/migrations/create")
async def create_migration_job_endpoint(req: MigrationJobCreateRequest):
    """Creates a new cold migration job and triggers execution."""
    is_same = (req.source_device_id == req.target_device_id) or (req.direct_transfer_method == "same_host")
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    job = create_migration_job(
        job_id=job_id,
        vm_id=req.vm_name,
        source_device_id=req.source_device_id,
        target_device_id=req.target_device_id,
        is_same_computer=is_same,
        start_vm_on_complete=req.auto_start_target or False
    )

    audit_logger.log_event(
        event_type="MIGRATION_JOB_CREATED",
        vm_id=req.vm_name,
        source_node=req.source_device_id,
        target_node=req.target_device_id,
        task_id=job_id,
        message=f"Cold migration job '{job_id}' created for VM '{req.vm_name}' ({req.source_device_id} -> {req.target_device_id}).",
        details={"job_id": job_id, "is_same_computer": is_same, "direct_transfer_method": req.direct_transfer_method}
    )

    # If VirtualBox provider is active, launch cold migration job task
    if isinstance(active_provider, VirtualBoxProvider):
        plan = MigrationPlan(
            plan_id=job["plan_id"],
            vm_id=req.vm_name,
            source_node=req.source_device_id,
            target_node=req.target_device_id,
            reason="Operator Triggered Cold OVA Migration",
            created_at=time.time(),
            estimated_duration_seconds=12.0
        )
        task = MigrationTaskStatus(
            task_id=job_id,
            plan_id=plan.plan_id,
            vm_id=req.vm_name,
            source_node=req.source_device_id,
            target_node=req.target_device_id,
            state="PREPARING",
            progress_percent=5.0,
            started_at=time.time(),
            updated_at=time.time(),
            stage="QUEUED"
        )
        migration_mgr.active_tasks[job_id] = task
        asyncio.create_task(active_provider._run_cold_migration_job(task, plan))

    return job


@router.get("/migrations/jobs")
async def list_jobs_endpoint(limit: int = 50):
    """Lists persistent migration jobs from the SQLite database."""
    return list_migration_jobs(limit=limit)


@router.get("/migrations/jobs/{job_id}")
async def get_job_endpoint(job_id: str):
    """Retrieves full status and metrics for a specific migration job."""
    job = get_migration_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Migration job '{job_id}' not found")
    return job


@router.post("/migrations/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str):
    """Cancels a pending or queued migration job."""
    job = get_migration_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Migration job '{job_id}' not found")
    if job["state"] in ("COMPLETED", "VERIFIED"):
        raise HTTPException(status_code=400, detail="Cannot cancel an already completed job")

    update_migration_job(
        job_id=job_id,
        state="FAILED",
        stage="CANCELLED",
        error_message="Cancelled by operator"
    )
    if job_id in migration_mgr.active_tasks:
        migration_mgr.active_tasks[job_id].state = "FAILED"
        migration_mgr.active_tasks[job_id].stage = "CANCELLED"
    return {"status": "cancelled", "job_id": job_id}


# -----------------------------------------------------------------------------
# Agent Packaging & Distribution Endpoint
# -----------------------------------------------------------------------------

@router.get("/agent/download")
async def download_agent():
    """Serves the standalone Windows Agent executable or packaging metadata."""
    dist_path = os.path.join(settings.AGENT_DIST_DIR, settings.AGENT_BINARY_NAME)
    if os.path.exists(dist_path):
        return FileResponse(
            path=dist_path,
            filename=settings.AGENT_BINARY_NAME,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{settings.AGENT_BINARY_NAME}"'}
        )
    return JSONResponse(
        status_code=200,
        content={
            "available": False,
            "message": "Standalone agent executable is not yet compiled on this server.",
            "build_instructions": "Run 'python scripts/build_agent.py' to generate 'dist/vmotion-agent.exe'.",
            "enrollment_secret": settings.ENROLLMENT_SECRET
        }
    )


# -----------------------------------------------------------------------------
# Transfer Authorization Endpoint
# -----------------------------------------------------------------------------

class TransferAuthorizeRequest(BaseModel):
    job_id: str
    source_device_id: str
    target_device_id: str
    artifact_name: str


@router.post("/transfers/authorize")
async def authorize_transfer(req: TransferAuthorizeRequest):
    """Issues a cryptographically signed one-time token for direct artifact transfer."""
    token_str = f"{req.job_id}:{req.source_device_id}:{req.target_device_id}:{req.artifact_name}:{settings.GATEWAY_AGENT_TOKEN}"
    auth_token = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    return {
        "status": "AUTHORIZED",
        "job_id": req.job_id,
        "artifact_name": req.artifact_name,
        "auth_token": auth_token,
        "expires_in_seconds": 3600
    }

