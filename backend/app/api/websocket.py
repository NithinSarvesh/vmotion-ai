"""
WebSocket Streaming Module for VMotion AI.
Broadcasts streaming telemetry, active migration updates, and audit timeline entries to frontend clients.
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

from app.api.routes import get_active_provider, migration_mgr, ppo_engine, deterministic_safety_gate, telemetry_engine
from app.audit.logger import audit_logger
from app.gateway.agent_gateway import agent_gateway
from app.config import settings

logger = logging.getLogger("agent-gateway")
ws_router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@ws_router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Gather fresh snapshot and aggregated telemetry
            agg_telemetry = await telemetry_engine.sample_telemetry()
            current_provider = get_active_provider()
            cluster = await current_provider.get_cluster_state()
            
            # Recommendation evaluation
            rec = None
            safety_eval = None
            if cluster.connected:
                rec = ppo_engine.evaluate(cluster)
                if rec.action_type == "MIGRATE" and rec.vm_id and rec.target_node:
                    proposal = migration_mgr.evaluate_and_propose(rec, cluster)
                    safety_eval = proposal.safety_evaluation if proposal else None

            # Active tasks & proposals
            active_tasks = [t.model_dump() for t in migration_mgr.active_tasks.values()]
            completed_tasks = [t.model_dump() for t in migration_mgr.completed_tasks[:10]]
            proposals = [p.model_dump() for p in migration_mgr.proposals.values()]
            audit_entries = [e.model_dump() for e in audit_logger.get_entries(limit=15)]
            active_agents = agent_gateway.list_agents()

            payload = {
                "type": "TELEMETRY_PULSE",
                "timestamp": cluster.timestamp,
                "cluster": cluster.model_dump(),
                "telemetry": agg_telemetry.model_dump(),
                "model_health": ppo_engine.get_health(),
                "recommendation": rec.model_dump() if rec else None,
                "safety_evaluation": safety_eval.model_dump() if safety_eval else None,
                "proposals": proposals,
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "audit_entries": audit_entries,
                "agents": active_agents
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@ws_router.websocket("/ws/agent")
async def websocket_agent_gateway_endpoint(
    websocket: WebSocket,
    host_id: str = "vbox-host-unknown",
    token: str = ""
):
    """
    Dedicated Cloud Agent Gateway endpoint.
    Remote physical host agents connect via persistent outbound WSS.
    Validates agent secret token, handles registration, telemetry ingestion,
    heartbeats, and command dispatch/response routing.
    """
    # 1. Authenticate token
    expected_token = settings.GATEWAY_AGENT_TOKEN
    provided_token = token or websocket.headers.get("X-Agent-Secret", "")

    # Check if host is enrolled in SQLite DB
    from app.db.database import get_device, hash_token
    device_rec = get_device(host_id)
    if device_rec and device_rec.get("is_revoked"):
        logger.warning(f"[Agent Gateway] Rejected connection for revoked device '{host_id}'.")
        await websocket.close(code=4001, reason="Unauthorized: Device has been revoked")
        return

    is_valid = False
    if expected_token and provided_token == expected_token:
        is_valid = True
    elif device_rec and device_rec.get("token_hash") and hash_token(provided_token) == device_rec.get("token_hash"):
        is_valid = True

    if not is_valid:
        logger.warning(
            f"[Agent Gateway] Authentication rejected for host '{host_id}'. "
            "Token mismatch: provided agent token does not match settings.GATEWAY_AGENT_TOKEN or device enrollment."
        )
        await websocket.close(code=4001, reason="Unauthorized: Invalid agent secret token")
        return

    await websocket.accept()
    registered_host_id = host_id

    try:
        while True:
            packet = await websocket.receive_json()
            packet_type = packet.get("type", "").upper()

            if packet_type == "REGISTER":
                registered_host_id = packet.get("host_id", host_id)
                hostname = packet.get("hostname", registered_host_id)
                lan_ip = packet.get("lan_ip")
                tailscale_ip = packet.get("tailscale_ip")
                vbox_ver = packet.get("vbox_version")
                agent_ver = packet.get("agent_version")

                await agent_gateway.register_agent(
                    host_id=registered_host_id,
                    websocket=websocket,
                    hostname=hostname,
                    lan_ip=lan_ip,
                    tailscale_ip=tailscale_ip,
                    vbox_version=vbox_ver,
                    agent_version=agent_ver
                )
                await websocket.send_json({
                    "type": "REGISTERED",
                    "host_id": registered_host_id,
                    "status": "ONLINE",
                    "timestamp": asyncio.get_event_loop().time()
                })

            elif packet_type == "HEARTBEAT":
                agent_gateway.record_heartbeat(registered_host_id)
                await websocket.send_json({
                    "type": "HEARTBEAT_ACK",
                    "timestamp": asyncio.get_event_loop().time()
                })

            elif packet_type == "TELEMETRY":
                telemetry_data = packet.get("data", packet)
                agent_gateway.record_telemetry(registered_host_id, telemetry_data)

            elif packet_type == "COMMAND_RESPONSE":
                correlation_id = packet.get("correlation_id", "")
                status = packet.get("status", "SUCCESS")
                data = packet.get("data")
                err = packet.get("error")
                agent_gateway.handle_command_response(
                    host_id=registered_host_id,
                    correlation_id=correlation_id,
                    status=status,
                    data=data,
                    error=err
                )

    except WebSocketDisconnect:
        await agent_gateway.unregister_agent(registered_host_id, websocket)
    except Exception as e:
        await agent_gateway.unregister_agent(registered_host_id, websocket)

