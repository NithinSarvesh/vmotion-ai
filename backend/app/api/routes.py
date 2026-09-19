"""
REST API Routes for VMotion AI Control Plane.
"""
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Literal, Optional

from app.providers.base import ClusterState, MigrationTaskStatus, ProviderConnectionResult
from app.providers.simulation import SimulationProvider
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

router = APIRouter(prefix="/api")

# Singleton state instances
simulation_provider = SimulationProvider()
proxmox_provider = ProxmoxVEProvider()
libvirt_provider = LibvirtKVMProvider()

current_provider_name = settings.PROVIDER_TYPE
active_provider = simulation_provider


def get_active_provider():
    global active_provider
    return active_provider


telemetry_engine = TelemetryEngine(active_provider)
migration_mgr = MigrationManager(active_provider)
ppo_engine = PPODecisionEngine()
rule_engine = RuleBasedDecisionEngine()
obs_adapter = ObservationAdapter()


class ModeSwitchRequest(BaseModel):
    provider_type: Literal["simulation", "proxmox", "libvirt"]
    confirm_live: bool = False


class ClusterConfigRequest(BaseModel):
    provider_type: Optional[Literal["simulation", "proxmox", "libvirt"]] = None
    proxmox_endpoint: Optional[str] = None
    proxmox_user: Optional[str] = None
    proxmox_token_id: Optional[str] = None
    proxmox_token_secret: Optional[str] = None
    proxmox_verify_ssl: Optional[bool] = None
    libvirt_uri: Optional[str] = None


class ConnectionTestRequest(BaseModel):
    provider_type: Literal["simulation", "proxmox", "libvirt"]
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


@router.get("/health")
async def health():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "provider": current_provider_name
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
    
    if req.provider_type in ("proxmox", "libvirt"):
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
        if req.provider_type == "proxmox":
            if not proxmox_provider.token_secret and not settings.PROXMOX_TOKEN_SECRET:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot switch to live Proxmox mode: API token secret is not configured."
                )

    if req.provider_type == "simulation":
        active_provider = simulation_provider
        current_provider_name = "simulation"
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
        "is_live": current_provider_name in ("proxmox", "libvirt"),
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
        await set_cluster_mode(ModeSwitchRequest(provider_type=req.provider_type))

    audit_logger.log_event(
        event_type="CONFIG_UPDATED",
        message=f"Infrastructure provider config updated. Provider: '{current_provider_name}'.",
        details={"provider": current_provider_name, "proxmox_endpoint": settings.PROXMOX_ENDPOINT}
    )
    return await get_cluster_config()


@router.post("/cluster/test-connection", response_model=ProviderConnectionResult)
async def test_connection(req: ConnectionTestRequest):
    if req.provider_type == "simulation":
        return await simulation_provider.test_connection()
    elif req.provider_type == "proxmox":
        endpoint = req.proxmox_endpoint or settings.PROXMOX_ENDPOINT
        user = req.proxmox_user or settings.PROXMOX_USER
        token_id = req.proxmox_token_id or settings.PROXMOX_TOKEN_ID
        if req.proxmox_token_secret is not None:
            token_secret = req.proxmox_token_secret.strip()
        else:
            token_secret = settings.PROXMOX_TOKEN_SECRET
        verify_ssl = req.proxmox_verify_ssl if req.proxmox_verify_ssl is not None else settings.PROXMOX_VERIFY_SSL

        test_pve = ProxmoxVEProvider(
            endpoint=endpoint,
            user=user,
            token_id=token_id,
            token_secret=token_secret,
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


@router.get("/ai/model/health")
async def get_model_health():
    return ppo_engine.get_health()


@router.get("/ai/recommendation")
async def get_recommendation():
    cluster = await active_provider.get_cluster_state()
    if not cluster.connected:
        raise HTTPException(status_code=503, detail="Cluster is disconnected. Cannot generate recommendations.")

    # Evaluate decision engine
    rec = ppo_engine.evaluate(cluster)
    
    # Evaluate safety gate & create proposal if migration is recommended
    proposal = None
    safety_eval = None
    if rec.action_type == "MIGRATE" and rec.vm_id and rec.target_node:
        safety_eval = deterministic_safety_gate.evaluate(cluster, rec.vm_id, rec.target_node)
        proposal = migration_mgr.evaluate_and_propose(rec, cluster)

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
        "safety_cooldown_seconds": settings.SAFETY_COOLDOWN_SECONDS
    }


@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    if req.enable_human_approval is not None:
        settings.ENABLE_HUMAN_APPROVAL = req.enable_human_approval
    if req.enable_autonomous_mode is not None:
        settings.ENABLE_AUTONOMOUS_MODE = req.enable_autonomous_mode
    return await get_settings()
