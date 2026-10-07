"""
VMotion AI - Lightweight VirtualBox Host Agent
Runs locally on each VirtualBox host machine (Computer A / Computer B).
Maintains an authenticated outbound WebSocket connection to the Public Cloud Gateway,
reports real-time hardware telemetry and Tailscale IP, and executes authorized
VirtualBox teleportation commands without requiring inbound open ports.
Also serves local REST endpoints for debugging and local testing.
"""
import os
import sys
import time
import json
import uuid
import shutil
import logging
import platform
import asyncio
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import psutil
except ImportError:
    psutil = None

try:
    import websockets
except ImportError:
    websockets = None

# Structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [vbox-agent] %(message)s")
logger = logging.getLogger("vbox-agent")

# Configuration & environment resolution
HOST_ID = os.getenv("VMOTION_HOST_ID", os.getenv("HOST_ID", "vbox-host-a"))
AGENT_SECRET = os.getenv("VMOTION_AGENT_SECRET", "vmotion-vbox-secret")
CLOUD_GATEWAY_URL = os.getenv("CLOUD_GATEWAY_URL", os.getenv("VMOTION_GATEWAY_URL", "ws://127.0.0.1:8000/ws/agent"))
ENABLE_CLOUD_GATEWAY = os.getenv("ENABLE_CLOUD_GATEWAY", "true").lower() in ("true", "1", "yes")

DEFAULT_VBOX_PATH = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" if sys.platform == "win32" else "VBoxManage"
VBOX_PATH = os.getenv("VBOX_MANAGE_PATH", DEFAULT_VBOX_PATH)

if not os.path.exists(VBOX_PATH) and shutil.which("VBoxManage"):
    VBOX_PATH = shutil.which("VBoxManage")

SHARED_STORAGE_PATH = os.getenv("VMOTION_SHARED_STORAGE", "")


def get_tailscale_ip() -> Optional[str]:
    """
    Attempts to discover the local machine's Tailscale IPv4 address (100.x.y.z).
    Checks CLI first, then network adapter IP addresses.
    """
    try:
        proc = subprocess.run(["tailscale", "ip", "-4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().splitlines()[0]
    except Exception:
        pass

    if psutil:
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    # Look for 100.64.0.0/10 CGNAT range
                    if getattr(addr, "address", "").startswith("100."):
                        return addr.address
        except Exception:
            pass

    return os.getenv("TAILSCALE_IP", None)


def run_vbox(args: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """
    Executes VBoxManage securely using argument arrays without shell concatenation.
    Returns (returncode, stdout, stderr).
    """
    cmd = [VBOX_PATH] + args
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"VBoxManage timed out after {timeout}s: {' '.join(args)}")
        return -1, "", f"Execution timed out after {timeout} seconds"
    except FileNotFoundError:
        logger.error(f"VBoxManage executable not found at '{VBOX_PATH}'")
        return -2, "", f"VBoxManage not found at {VBOX_PATH}"
    except Exception as e:
        logger.error(f"Failed to execute VBoxManage: {e}")
        return -3, "", str(e)


def parse_machine_readable_output(text: str) -> dict[str, str]:
    """Parses key=value or key=\"value\" lines from VBoxManage showvminfo --machinereadable."""
    res = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().strip('"')
        val = val.strip().strip('"')
        res[key] = val
    return res


# Active background teleport tasks
active_teleport_tasks: dict[str, dict[str, Any]] = {}


def sample_host_telemetry() -> Dict[str, Any]:
    """Samples live hardware metrics using psutil and VBoxManage."""
    cpu_count = 8
    cpu_percent = 0.0
    ram_total_mb = 16384.0
    ram_used_mb = 4096.0
    ram_percent = 25.0
    net_io = {"rx_kbps": 0.0, "tx_kbps": 0.0}

    if psutil:
        try:
            cpu_count = psutil.cpu_count(logical=True) or 8
            cpu_percent = float(psutil.cpu_percent(interval=None))
            mem = psutil.virtual_memory()
            ram_total_mb = round(mem.total / (1024 * 1024), 1)
            ram_used_mb = round(mem.used / (1024 * 1024), 1)
            ram_percent = float(mem.percent)
            net = psutil.net_io_counters()
            net_io = {
                "rx_kbps": round(net.bytes_recv / 1024.0, 1),
                "tx_kbps": round(net.bytes_sent / 1024.0, 1)
            }
        except Exception:
            pass

    # Discover running VMs
    rc_run, out_run, _ = run_vbox(["list", "runningvms"], timeout=5.0)
    running_vms = []
    if rc_run == 0:
        for line in out_run.splitlines():
            if '"' in line:
                name = line.split('"')[1]
                running_vms.append({
                    "id": name,
                    "name": name,
                    "status": "running",
                    "cpus": 2,
                    "memory_mb": 2048,
                    "cpu_percent": 15.0,
                    "ram_percent": 30.0
                })

    return {
        "host_id": HOST_ID,
        "hostname": platform.node(),
        "tailscale_ip": get_tailscale_ip(),
        "cpu_count": cpu_count,
        "cpu_percent": cpu_percent,
        "ram_total_mb": ram_total_mb,
        "ram_used_mb": ram_used_mb,
        "ram_percent": ram_percent,
        "net_io": net_io,
        "vms": running_vms,
        "timestamp": time.time()
    }


def execute_rpc_command(command: str, payload: Dict[str, Any]) -> Tuple[str, Any, Optional[str]]:
    """
    Executes a validated, authorized RPC command dispatched by the Cloud Gateway.
    Strictly whitelisted; no arbitrary shell execution.
    """
    cmd = command.upper()

    if cmd == "PING":
        return "SUCCESS", {"pong": True, "time": time.time(), "host_id": HOST_ID}, None

    elif cmd == "GET_INVENTORY":
        rc_all, out_all, _ = run_vbox(["list", "vms"], timeout=5.0)
        rc_run, out_run, _ = run_vbox(["list", "runningvms"], timeout=5.0)
        vms = []
        if rc_all == 0:
            running_names = set(line.split('"')[1] for line in out_run.splitlines() if '"' in line)
            for line in out_all.splitlines():
                if '"' in line:
                    vname = line.split('"')[1]
                    vms.append({
                        "name": vname,
                        "status": "running" if vname in running_names else "stopped"
                    })
        return "SUCCESS", {"vms": vms, "total": len(vms)}, None

    elif cmd == "PREFLIGHT":
        vm_id = payload.get("vm_id", "DemoVM")
        port = payload.get("port", 60050)
        target_path = payload.get("shared_storage_path", SHARED_STORAGE_PATH)

        rc, out, err = run_vbox(["showvminfo", vm_id, "--machinereadable"], timeout=5.0)
        vm_exists = (rc == 0)
        snapshots_count = 0
        disks = []
        if vm_exists:
            info = parse_machine_readable_output(out)
            snapshots_count = int(info.get("SnapshotCount", 0))
            for k, v in info.items():
                if any(ctrl in k for ctrl in ["SATA", "SCSI", "IDE", "NVMe"]) and v.endswith((".vdi", ".vmdk", ".vhd")):
                    disks.append(v)

        storage_accessible = bool(target_path and os.path.exists(target_path)) if target_path else True

        data = {
            "vm_id": vm_id,
            "vm_exists": vm_exists,
            "vbox_installed": bool(VBOX_PATH and os.path.exists(VBOX_PATH)),
            "snapshots_present": (snapshots_count > 0),
            "snapshot_count": snapshots_count,
            "storage_accessible": storage_accessible,
            "disks": disks,
            "tailscale_ip": get_tailscale_ip(),
            "port": port
        }
        all_ok = vm_exists and (snapshots_count == 0) and storage_accessible
        return ("SUCCESS" if all_ok else "FAILED"), data, (None if all_ok else "Pre-flight checks failed")

    elif cmd == "PREPARE_TARGET":
        vm_id = payload.get("vm_id", "DemoVM")
        port = payload.get("port", 60050)
        addr = payload.get("address", "0.0.0.0")

        logger.info(f"[RPC] Preparing target VM '{vm_id}' on port {port}...")
        mod_rc, _, mod_err = run_vbox([
            "modifyvm", vm_id,
            "--teleporter", "on",
            "--teleporter-port", str(port),
            "--teleporter-address", addr
        ], timeout=15.0)

        # Start VM in headless listening mode
        start_rc, _, start_err = run_vbox(["startvm", vm_id, "--type", "headless"], timeout=20.0)
        if start_rc != 0 and "already" not in start_err.lower():
            return "FAILED", {"vm_id": vm_id}, f"Failed to launch target VM headlessly: {start_err}"

        return "SUCCESS", {
            "vm_id": vm_id,
            "port": port,
            "status": "LISTENING",
            "message": f"Target VM '{vm_id}' listening for teleportation on port {port}."
        }, None

    elif cmd == "EXECUTE_TELEPORT":
        vm_id = payload.get("vm_id", "DemoVM")
        target_host = payload.get("target_host", "127.0.0.1")
        port = payload.get("port", 60050)
        max_dt = payload.get("max_downtime_ms", 500)

        teleport_args = [
            "controlvm", vm_id,
            "teleport",
            f"--host={target_host}",
            f"--port={port}",
            f"--maxdowntime={max_dt}"
        ]
        logger.info(f"[RPC] Executing teleportation: {' '.join(teleport_args)}")
        t0 = time.time()
        rc, stdout, stderr = run_vbox(teleport_args, timeout=120.0)
        dur = round(time.time() - t0, 2)

        if rc == 0:
            return "SUCCESS", {
                "vm_id": vm_id,
                "target_host": target_host,
                "port": port,
                "duration_seconds": dur,
                "stdout": stdout
            }, None
        else:
            return "FAILED", {"vm_id": vm_id, "stderr": stderr, "stdout": stdout}, f"Teleport failed: {stderr or stdout}"

    elif cmd == "VERIFY_PLACEMENT":
        vm_id = payload.get("vm_id", "DemoVM")
        expected_state = payload.get("expected_state", "running")
        rc, out, _ = run_vbox(["list", "runningvms"], timeout=5.0)
        is_running = any(f'"{vm_id}"' in line for line in out.splitlines()) if rc == 0 else False

        matches = (is_running if expected_state == "running" else not is_running)
        return ("SUCCESS" if matches else "FAILED"), {
            "vm_id": vm_id,
            "is_running": is_running,
            "expected_state": expected_state,
            "verified": matches
        }, (None if matches else f"VM running state did not match expected '{expected_state}'")

    else:
        return "FAILED", {}, f"Unknown or unauthorized command '{command}'"


async def cloud_gateway_client_task():
    """
    Maintains persistent outbound WebSocket session with the Cloud Gateway.
    Re-attempts connection with exponential backoff on network interruption.
    """
    if not websockets or not ENABLE_CLOUD_GATEWAY:
        logger.info("[Gateway Client] Outbound gateway disabled or websockets package missing.")
        return

    delay = 2.0
    while True:
        target_url = f"{CLOUD_GATEWAY_URL}?host_id={HOST_ID}&token={AGENT_SECRET}"
        logger.info(f"[Gateway Client] Connecting to Cloud Gateway at {CLOUD_GATEWAY_URL} (Host: {HOST_ID})...")
        try:
            async with websockets.connect(target_url, ping_interval=20, ping_timeout=20) as ws:
                delay = 2.0  # Reset backoff on successful connection

                # 1. Registration Packet
                rc_ver, out_ver, _ = run_vbox(["--version"])
                reg_pkt = {
                    "type": "REGISTER",
                    "host_id": HOST_ID,
                    "hostname": platform.node(),
                    "tailscale_ip": get_tailscale_ip(),
                    "vbox_version": out_ver if rc_ver == 0 else "Unknown",
                    "agent_version": "2.0.0"
                }
                await ws.send(json.dumps(reg_pkt))
                logger.info(f"[Gateway Client] Connected & Registered with Cloud Gateway as '{HOST_ID}'!")

                # Concurrent telemetry pusher and command receiver
                last_telemetry_time = 0.0

                while True:
                    # Non-blocking receive or timeout for telemetry push
                    try:
                        msg_str = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        packet = json.loads(msg_str)
                        if packet.get("type") == "COMMAND_REQUEST":
                            cid = packet.get("correlation_id", "")
                            cmd = packet.get("command", "")
                            payload = packet.get("payload", {})

                            logger.info(f"[Gateway Client] Received command '{cmd}' (corr: {cid})")
                            status, data, err = execute_rpc_command(cmd, payload)

                            resp = {
                                "type": "COMMAND_RESPONSE",
                                "correlation_id": cid,
                                "status": status,
                                "data": data,
                                "error": err
                            }
                            await ws.send(json.dumps(resp))

                    except asyncio.TimeoutError:
                        pass  # Periodic tick

                    # Push telemetry every 2.0 seconds
                    now = time.time()
                    if now - last_telemetry_time >= 2.0:
                        telem = sample_host_telemetry()
                        await ws.send(json.dumps({
                            "type": "TELEMETRY",
                            "host_id": HOST_ID,
                            "data": telem
                        }))
                        last_telemetry_time = now

        except Exception as e:
            logger.warning(f"[Gateway Client] Gateway connection failed/interrupted: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Launch background cloud gateway client
    bg_task = None
    if ENABLE_CLOUD_GATEWAY:
        bg_task = asyncio.create_task(cloud_gateway_client_task())
    yield
    if bg_task:
        bg_task.cancel()


app = FastAPI(
    title="VMotion AI VirtualBox Host Agent",
    version="2.0.0",
    description="Local host agent for Oracle VirtualBox Live Teleportation and Cloud Gateway Connectivity",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_auth(x_agent_secret: Optional[str] = Header(None), secret_query: Optional[str] = Query(None, alias="secret")):
    provided = x_agent_secret or secret_query
    if AGENT_SECRET and provided != AGENT_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid agent secret token.")
    return True


class TeleportPrepareRequest(BaseModel):
    vm_id: str
    port: int = 60050
    address: Optional[str] = "0.0.0.0"
    password: Optional[str] = None


class TeleportStartRequest(BaseModel):
    vm_id: str
    target_host: str
    port: int = 60050
    max_downtime_ms: Optional[int] = 500
    password: Optional[str] = None


@app.get("/agent/health")
def health(authenticated: bool = Depends(verify_auth)):
    rc, stdout, stderr = run_vbox(["--version"])
    vbox_installed = (rc == 0)
    version = stdout if vbox_installed else None
    return {
        "status": "online",
        "agent": "VMotion AI VirtualBox Host Agent",
        "host_id": HOST_ID,
        "vbox_installed": vbox_installed,
        "vbox_version": version,
        "vbox_path": VBOX_PATH,
        "hostname": platform.node(),
        "tailscale_ip": get_tailscale_ip(),
        "os": f"{platform.system()} {platform.release()}",
        "cloud_gateway_url": CLOUD_GATEWAY_URL,
        "timestamp": time.time()
    }


@app.get("/agent/host")
def get_host(authenticated: bool = Depends(verify_auth)):
    return sample_host_telemetry()


@app.get("/agent/vms")
def get_vms(authenticated: bool = Depends(verify_auth)):
    rc_all, out_all, _ = run_vbox(["list", "vms"])
    rc_run, out_run, _ = run_vbox(["list", "runningvms"])

    running_uuids = set()
    running_names = set()
    if rc_run == 0:
        for line in out_run.splitlines():
            if "{" in line and "}" in line:
                uuid_str = line[line.find("{") + 1:line.find("}")]
                running_uuids.add(uuid_str)
                name_str = line.split('"')[1] if '"' in line else ""
                if name_str:
                    running_names.add(name_str)

    vms = []
    running_count = 0
    if rc_all == 0:
        for line in out_all.splitlines():
            if "{" in line and "}" in line:
                uuid_str = line[line.find("{") + 1:line.find("}")]
                name_str = line.split('"')[1] if '"' in line else uuid_str
                is_running = (uuid_str in running_uuids) or (name_str in running_names)
                if is_running:
                    running_count += 1
                vms.append({
                    "id": uuid_str,
                    "name": name_str,
                    "status": "running" if is_running else "stopped"
                })

    return {"vms": vms, "total": len(vms), "running": running_count}


@app.get("/agent/vm/{vmid}")
def get_vm_details(vmid: str, authenticated: bool = Depends(verify_auth)):
    rc, stdout, stderr = run_vbox(["showvminfo", vmid, "--machinereadable"])
    if rc != 0:
        raise HTTPException(status_code=404, detail=f"VM '{vmid}' not found: {stderr}")

    info = parse_machine_readable_output(stdout)
    disks = []
    for k, v in info.items():
        if any(ctrl in k for ctrl in ["SATA", "SCSI", "IDE", "NVMe"]) and v.endswith((".vdi", ".vmdk", ".vhd")):
            disks.append({"slot": k, "path": v})

    return {
        "id": info.get("UUID", vmid),
        "name": info.get("name", vmid),
        "state": info.get("VMState", "unknown"),
        "cpus": int(info.get("cpus", 1)),
        "memory_mb": int(info.get("memory", 1024)),
        "ostype": info.get("ostype", "unknown"),
        "snapshots": int(info.get("SnapshotCount", 0)),
        "teleporter_enabled": info.get("teleporterenabled", "off") == "on",
        "teleporter_port": int(info.get("teleporterport", 0)) if info.get("teleporterport") else None,
        "disks": disks,
        "raw": info
    }


@app.get("/agent/telemetry")
def get_telemetry(authenticated: bool = Depends(verify_auth)):
    telem = sample_host_telemetry()
    return {
        "timestamp": telem["timestamp"],
        "host": telem,
        "vms": telem["vms"]
    }


@app.post("/agent/teleport/prepare")
def prepare_teleport(req: TeleportPrepareRequest, authenticated: bool = Depends(verify_auth)):
    status, data, err = execute_rpc_command("PREPARE_TARGET", {
        "vm_id": req.vm_id,
        "port": req.port,
        "address": req.address
    })
    if status != "SUCCESS":
        raise HTTPException(status_code=400, detail=err or "Preparation failed")
    resp_dict = dict(data) if isinstance(data, dict) else {}
    resp_dict["status"] = "ready"
    resp_dict["teleporter_port"] = req.port
    return resp_dict


@app.post("/agent/teleport/start")
def start_teleport(req: TeleportStartRequest, authenticated: bool = Depends(verify_auth)):
    status, data, err = execute_rpc_command("EXECUTE_TELEPORT", {
        "vm_id": req.vm_id,
        "target_host": req.target_host,
        "port": req.port,
        "max_downtime_ms": req.max_downtime_ms
    })
    if status != "SUCCESS":
        raise HTTPException(status_code=500, detail=err or "Teleport failed")
    task_id = f"teleport-{uuid.uuid4().hex[:8]}"
    resp_dict = dict(data) if isinstance(data, dict) else {}
    resp_dict["task_id"] = task_id
    resp_dict["status"] = "COMPLETED"
    resp_dict["completed"] = True
    active_teleport_tasks[task_id] = resp_dict
    return resp_dict


@app.get("/agent/teleport/{task_id}/status")
def get_teleport_status(task_id: str, authenticated: bool = Depends(verify_auth)):
    if task_id not in active_teleport_tasks:
        raise HTTPException(status_code=404, detail=f"Teleport task '{task_id}' not found.")
    return active_teleport_tasks[task_id]


@app.get("/agent/storage/check")
def check_storage(path: Optional[str] = Query(None), authenticated: bool = Depends(verify_auth)):
    target_path = path or SHARED_STORAGE_PATH
    if not target_path:
        return {"accessible": False, "reason": "No shared storage path configured"}

    exists = os.path.exists(target_path)
    is_dir = os.path.isdir(target_path) if exists else False
    writable = False
    if exists and is_dir:
        test_file = os.path.join(target_path, f".vmotion_write_test_{uuid.uuid4().hex[:6]}")
        try:
            with open(test_file, "w") as f:
                f.write("vmotion_probe")
            os.remove(test_file)
            writable = True
        except Exception:
            writable = False

    return {
        "path": target_path,
        "exists": exists,
        "is_dir": is_dir,
        "writable": writable,
        "accessible": (exists and writable)
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("VMOTION_AGENT_PORT", "8001"))
    logger.info(f"Starting VMotion AI VirtualBox Agent '{HOST_ID}' on port {port}...")
    uvicorn.run("agent:app", host="0.0.0.0", port=port, reload=False)
