"""
WebSocket Streaming Module for VMotion AI.
Broadcasts streaming telemetry, active migration updates, and audit timeline entries to frontend clients.
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

from app.api.routes import get_active_provider, migration_mgr, ppo_engine, deterministic_safety_gate, telemetry_engine
from app.audit.logger import audit_logger

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
                    safety_eval = deterministic_safety_gate.evaluate(cluster, rec.vm_id, rec.target_node)
                    # Automatically track proposal if not already present
                    migration_mgr.evaluate_and_propose(rec, cluster)

            # Active tasks & proposals
            active_tasks = [t.model_dump() for t in migration_mgr.active_tasks.values()]
            completed_tasks = [t.model_dump() for t in migration_mgr.completed_tasks[:10]]
            proposals = [p.model_dump() for p in migration_mgr.proposals.values()]
            audit_entries = [e.model_dump() for e in audit_logger.get_entries(limit=15)]

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
                "audit_entries": audit_entries
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
