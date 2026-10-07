"""
VMotion AI - Cloud Agent Gateway Module.
Maintains persistent outbound WebSocket sessions from remote physical VirtualBox host agents.
Tracks host online/offline state, receives real-time telemetry, routes RPC commands
with correlation IDs, and handles request timeouts.
"""
import time
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any, List
from fastapi import WebSocket

from app.config import settings
from dataclasses import dataclass

from app.audit.logger import audit_logger

logger = logging.getLogger("vmotion.gateway")


class AgentOfflineError(Exception):
    """Raised when attempting to command an agent that is disconnected or timed out."""
    pass


class AgentCommandTimeoutError(Exception):
    """Raised when an agent does not reply to an RPC command within the configured timeout."""
    pass


@dataclass
class AgentCommandResponse:
    status: str
    data: Any = None
    error: Optional[str] = None
    host_id: str = ""


class AgentSession:
    """Represents an active physical host agent connected over WebSocket."""
    def __init__(
        self,
        host_id: str,
        websocket: WebSocket,
        hostname: str = "",
        tailscale_ip: Optional[str] = None,
        vbox_version: Optional[str] = None,
        agent_version: Optional[str] = None,
    ):
        self.host_id = host_id
        self.websocket = websocket
        self.hostname = hostname or host_id
        self.tailscale_ip = tailscale_ip
        self.vbox_version = vbox_version
        self.agent_version = agent_version
        self.connected_at = time.time()
        self.last_heartbeat_at = time.time()
        self.latest_telemetry: Optional[Dict[str, Any]] = None
        self.pending_commands: Dict[str, asyncio.Future] = {}

    @property
    def agent_id(self) -> str:
        return self.host_id

    @property
    def last_heartbeat(self) -> float:
        return self.last_heartbeat_at

    @last_heartbeat.setter
    def last_heartbeat(self, val: float):
        self.last_heartbeat_at = val

    @property
    def ping_latency_ms(self) -> Optional[float]:
        return round((time.time() - self.last_heartbeat_at) * 1000, 1)

    def is_alive(self, timeout_seconds: float) -> bool:
        return (time.time() - self.last_heartbeat_at) <= timeout_seconds

    def to_dict(self, timeout_seconds: float) -> Dict[str, Any]:
        alive = self.is_alive(timeout_seconds)
        latency = round((time.time() - self.last_heartbeat_at) * 1000, 1)
        return {
            "host_id": self.host_id,
            "hostname": self.hostname,
            "status": "online" if alive else "offline",
            "tailscale_ip": self.tailscale_ip,
            "vbox_version": self.vbox_version,
            "agent_version": self.agent_version,
            "connected_at": self.connected_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "latency_ms": latency if alive else None,
            "has_telemetry": self.latest_telemetry is not None
        }


class CloudAgentGateway:
    """
    Central gateway maintaining sessions for all remote host agents.
    Thread-safe and async-compatible.
    """

    def __init__(self):
        self._sessions: Dict[str, AgentSession] = {}
        self._lock = asyncio.Lock()

    async def register_agent(
        self,
        host_id: str,
        websocket: WebSocket,
        hostname: str = "",
        tailscale_ip: Optional[str] = None,
        vbox_version: Optional[str] = None,
        agent_version: Optional[str] = None
    ) -> AgentSession:
        """Registers or updates an active host agent connection."""
        async with self._lock:
            # If an old session existed for this host, cancel any pending commands
            if host_id in self._sessions:
                old_session = self._sessions[host_id]
                for cid, fut in list(old_session.pending_commands.items()):
                    if not fut.done():
                        fut.set_exception(AgentOfflineError(f"Agent session for '{host_id}' reconnected."))

            session = AgentSession(
                host_id=host_id,
                websocket=websocket,
                hostname=hostname,
                tailscale_ip=tailscale_ip,
                vbox_version=vbox_version,
                agent_version=agent_version
            )
            self._sessions[host_id] = session

            logger.info(
                f"[Gateway] Host Agent '{host_id}' registered successfully. "
                f"Hostname: '{hostname}', Tailscale: '{tailscale_ip}', VBox: '{vbox_version}'"
            )
            audit_logger.log_event(
                event_type="CLUSTER_CONNECTED",
                message=f"Host Agent '{host_id}' connected via outbound WSS.",
                details={
                    "host_id": host_id,
                    "hostname": hostname,
                    "tailscale_ip": tailscale_ip,
                    "vbox_version": vbox_version
                }
            )
            return session

    async def unregister_agent(self, host_id: str, websocket: Optional[WebSocket] = None):
        """Unregisters an agent on disconnect."""
        async with self._lock:
            session = self._sessions.get(host_id)
            if session:
                if websocket is None or session.websocket == websocket:
                    for cid, fut in list(session.pending_commands.items()):
                        if not fut.done():
                            fut.set_exception(AgentOfflineError(f"Agent '{host_id}' disconnected."))
                    self._sessions.pop(host_id, None)
                    logger.warning(f"[Gateway] Host Agent '{host_id}' unregistered / disconnected.")
                    audit_logger.log_event(
                        event_type="CLUSTER_DISCONNECTED",
                        message=f"Host Agent '{host_id}' disconnected from Cloud Gateway.",
                        details={"host_id": host_id}
                    )

    def get_session(self, host_id: str) -> Optional[AgentSession]:
        return self._sessions.get(host_id)

    def is_agent_online(self, host_id: str) -> bool:
        session = self._sessions.get(host_id)
        if not session:
            return False
        return session.is_alive(settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS)

    def record_telemetry(self, host_id: str, telemetry_data: Dict[str, Any]):
        """Records telemetry payload and updates heartbeat timestamp."""
        session = self._sessions.get(host_id)
        if session:
            session.last_heartbeat_at = time.time()
            session.latest_telemetry = telemetry_data
            # Update Tailscale IP or host specs if provided in telemetry
            if "tailscale_ip" in telemetry_data and telemetry_data["tailscale_ip"]:
                session.tailscale_ip = telemetry_data["tailscale_ip"]
            if "hostname" in telemetry_data and telemetry_data["hostname"]:
                session.hostname = telemetry_data["hostname"]

    def record_heartbeat(self, host_id: str, latency_ms: Optional[float] = None):
        session = self._sessions.get(host_id)
        if session:
            session.last_heartbeat_at = time.time()

    def update_telemetry(self, host_id: str, telemetry_data: Dict[str, Any]):
        self.record_telemetry(host_id, telemetry_data)

    def list_agents(self) -> List[Dict[str, Any]]:
        timeout = settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS
        return [session.to_dict(timeout) for session in self._sessions.values()]

    def list_active_agents(self) -> List[Dict[str, Any]]:
        return self.list_agents()

    async def send_command(
        self,
        host_id: str,
        command: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Sends an authenticated RPC command to a remote agent over its persistent WebSocket.
        Correlates response using unique correlation_id and awaits completion.
        """
        session = self._sessions.get(host_id)
        if not session or not session.is_alive(settings.AGENT_HEARTBEAT_TIMEOUT_SECONDS):
            err_msg = f"Cannot send command '{command}': Host Agent '{host_id}' is offline or not connected."
            logger.error(f"[Gateway] {err_msg}")
            raise AgentOfflineError(err_msg)

        correlation_id = f"cmd-{uuid.uuid4().hex[:12]}"
        fut = asyncio.get_running_loop().create_future()
        session.pending_commands[correlation_id] = fut

        request_packet = {
            "type": "COMMAND_REQUEST",
            "correlation_id": correlation_id,
            "command": command,
            "payload": payload or {},
            "timestamp": time.time()
        }

        try:
            logger.info(f"[Gateway] Dispatching '{command}' to '{host_id}' (corr: {correlation_id})")
            if hasattr(session.websocket, "send_json") and callable(session.websocket.send_json):
                await session.websocket.send_json(request_packet)
            else:
                import json
                await session.websocket.send_text(json.dumps(request_packet))
            result = await asyncio.wait_for(fut, timeout=timeout)
            logger.info(f"[Gateway] Command '{command}' on '{host_id}' completed (corr: {correlation_id})")
            return result
        except asyncio.TimeoutError:
            err = f"Command '{command}' to agent '{host_id}' timed out after {timeout}s."
            logger.error(f"[Gateway] {err} (corr: {correlation_id})")
            raise AgentCommandTimeoutError(err)
        finally:
            session.pending_commands.pop(correlation_id, None)

    async def dispatch_command(
        self,
        agent_id: str,
        command: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 30.0
    ) -> AgentCommandResponse:
        """Convenience method returning typed AgentCommandResponse."""
        res = await self.send_command(host_id=agent_id, command=command, payload=payload, timeout=timeout_seconds)
        return AgentCommandResponse(
            status=res.get("status", "FAILED"),
            data=res.get("data"),
            error=res.get("error"),
            host_id=res.get("host_id", agent_id)
        )

    def handle_command_response(
        self,
        host_id: str,
        correlation_id: str,
        status: str,
        data: Any = None,
        error: Optional[str] = None
    ):
        """Resolves the awaiting future with the command response from the agent."""
        session = self._sessions.get(host_id)
        if not session:
            logger.warning(f"[Gateway] Received response for non-existent session '{host_id}'")
            return

        fut = session.pending_commands.get(correlation_id)
        if not fut:
            logger.warning(f"[Gateway] Received response for unknown correlation ID '{correlation_id}'")
            return

        if not fut.done():
            fut.set_result({
                "status": status,
                "data": data,
                "error": error,
                "host_id": host_id
            })

    def resolve_response(
        self,
        correlation_id: str,
        status: str,
        data: Any = None,
        error: Optional[str] = None
    ):
        """Finds and resolves the pending command matching correlation_id across all sessions."""
        for host_id, session in self._sessions.items():
            if correlation_id in session.pending_commands:
                self.handle_command_response(host_id, correlation_id, status, data, error)
                return


# Global singleton instance
agent_gateway = CloudAgentGateway()
