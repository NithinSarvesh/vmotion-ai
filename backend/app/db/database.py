"""
VMotion AI - SQLite Persistence Layer.
Manages persistent storage for:
- Enrolled Devices (Host & Target multi-device registry)
- Published VM Catalog (VM metadata published by hosts)
- Migration Jobs (Explicit 10-state lifecycle FSM)
- Audit Event Ledger (Immutable operational transition logs)
"""
import os
import time
import json
import sqlite3
import hashlib
import hmac
import secrets
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("vmotion.db")

DEFAULT_DB_FILE = os.getenv("DATABASE_PATH", "vmotion.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    if custom_path:
        return custom_path
    from app.config import settings
    return getattr(settings, "DATABASE_PATH", DEFAULT_DB_FILE)


_INITIALIZED_DBS = set()


def _raw_connection(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    if path not in _INITIALIZED_DBS:
        _INITIALIZED_DBS.add(path)
        init_db(path)
    return _raw_connection(path)


def init_db(db_path: Optional[str] = None):
    """Initializes tables in the SQLite database if they do not exist."""
    path = get_db_path(db_path)
    _INITIALIZED_DBS.add(path)
    logger.info(f"[DB] Initializing database at '{path}'")
    with _raw_connection(path) as conn:
        cursor = conn.cursor()

        # 1. Devices Table (Multi-Device Enrollment Registry)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'both',
            owner_name TEXT DEFAULT 'Default User',
            agent_version TEXT DEFAULT '2.0.0',
            vbox_version TEXT,
            lan_ip TEXT,
            tailscale_ip TEXT,
            status TEXT NOT NULL DEFAULT 'offline',
            token_hash TEXT,
            enrolled_at REAL NOT NULL,
            last_heartbeat_at REAL NOT NULL,
            is_revoked INTEGER NOT NULL DEFAULT 0
        );
        """)

        # 2. Published VM Catalog Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS published_vms (
            vm_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'stopped',
            cpu_cores INTEGER NOT NULL DEFAULT 2,
            ram_mb REAL NOT NULL DEFAULT 2048.0,
            disk_gb REAL NOT NULL DEFAULT 20.0,
            os_type TEXT DEFAULT 'other',
            is_published INTEGER NOT NULL DEFAULT 1,
            updated_at REAL NOT NULL,
            PRIMARY KEY (vm_id, device_id),
            FOREIGN KEY (device_id) REFERENCES devices (device_id) ON DELETE CASCADE
        );
        """)

        # 3. Migration Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS migration_jobs (
            job_id TEXT PRIMARY KEY,
            plan_id TEXT,
            vm_id TEXT NOT NULL,
            source_device_id TEXT NOT NULL,
            target_device_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'QUEUED',
            stage TEXT NOT NULL DEFAULT 'PREFLIGHT',
            progress_percent REAL NOT NULL DEFAULT 0.0,
            file_size_bytes INTEGER DEFAULT 0,
            file_size_mb REAL DEFAULT 0.0,
            sha256 TEXT,
            export_duration_seconds REAL,
            transfer_duration_seconds REAL,
            import_duration_seconds REAL,
            imported_vm_name TEXT,
            error_message TEXT,
            is_same_computer INTEGER NOT NULL DEFAULT 0,
            start_vm_on_complete INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            completed_at REAL
        );
        """)

        try:
            cursor.execute("ALTER TABLE migration_jobs ADD COLUMN completed_at REAL;")
        except sqlite3.OperationalError:
            pass

        # 4. Audit Events Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            timestamp REAL NOT NULL,
            time_iso TEXT NOT NULL,
            event_type TEXT NOT NULL,
            vm_id TEXT,
            source_node TEXT,
            target_node TEXT,
            task_id TEXT,
            message TEXT NOT NULL,
            details_json TEXT
        );
        """)

        # 5. Transfer Authorizations Table (Scoped, Cryptographically Signed, Single-Use)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfer_authorizations (
            token_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            source_device_id TEXT NOT NULL,
            target_device_id TEXT NOT NULL,
            artifact_name TEXT NOT NULL,
            hmac_signature TEXT NOT NULL,
            issued_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            is_redeemed INTEGER NOT NULL DEFAULT 0,
            redeemed_at REAL
        );
        """)

        conn.commit()
    logger.info("[DB] Database initialization complete.")


# -----------------------------------------------------------------------------
# Device Enrollment & Registry Operations
# -----------------------------------------------------------------------------

def hash_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest() if token else ""


def enroll_device(
    device_id: str,
    hostname: str,
    role: str = "both",
    owner_name: str = "Default User",
    agent_version: str = "2.0.0",
    token: str = "",
    vbox_version: Optional[str] = None,
    lan_ip: Optional[str] = None,
    tailscale_ip: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Registers or updates a device enrollment in the persistent registry."""
    now = time.time()
    token_h = hash_token(token) if token else ""

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO devices (
            device_id, hostname, role, owner_name, agent_version, vbox_version,
            lan_ip, tailscale_ip, status, token_hash, enrolled_at, last_heartbeat_at, is_revoked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?, ?, 0)
        ON CONFLICT(device_id) DO UPDATE SET
            hostname=excluded.hostname,
            role=excluded.role,
            owner_name=excluded.owner_name,
            agent_version=excluded.agent_version,
            vbox_version=COALESCE(excluded.vbox_version, devices.vbox_version),
            lan_ip=COALESCE(excluded.lan_ip, devices.lan_ip),
            tailscale_ip=COALESCE(excluded.tailscale_ip, devices.tailscale_ip),
            status='online',
            token_hash=CASE WHEN excluded.token_hash != '' THEN excluded.token_hash ELSE devices.token_hash END,
            last_heartbeat_at=excluded.last_heartbeat_at,
            is_revoked=0;
        """, (device_id, hostname, role, owner_name, agent_version, vbox_version, lan_ip, tailscale_ip, token_h, now, now))
        conn.commit()

    return get_device(device_id, db_path=db_path) or {}


# Backward compatibility alias
register_device = enroll_device


def get_device(device_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_device_by_token(token: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Looks up an active, non-revoked device matching the SHA-256 hash of the provided token."""
    if not token or not token.strip():
        return None
    token_h = hash_token(token)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE token_hash = ? AND is_revoked = 0", (token_h,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d.pop("token_hash", None)
        return d


def sanitize_device(device: Dict[str, Any], is_operator: bool = False) -> Dict[str, Any]:
    """
    Sanitizes device records before returning them across public APIs.
    Always removes token_hash. Masks sensitive network IPs unless the caller is an authenticated Operator.
    """
    out = dict(device)
    out.pop("token_hash", None)
    if not is_operator:
        lan = out.get("lan_ip")
        if lan and "." in lan:
            parts = lan.split(".")
            out["lan_ip"] = f"{parts[0]}.{parts[1]}.{parts[2]}.***" if len(parts) == 4 else "***"
        ts = out.get("tailscale_ip")
        if ts and "." in ts:
            parts = ts.split(".")
            out["tailscale_ip"] = f"{parts[0]}.{parts[1]}.***.***" if len(parts) == 4 else "***"
    return out


def list_devices(include_revoked: bool = False, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if include_revoked:
            cursor.execute("SELECT * FROM devices ORDER BY enrolled_at DESC")
        else:
            cursor.execute("SELECT * FROM devices WHERE is_revoked = 0 ORDER BY enrolled_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_device_heartbeat(
    device_id: str,
    lan_ip: Optional[str] = None,
    tailscale_ip: Optional[str] = None,
    vbox_version: Optional[str] = None,
    status: str = "online",
    db_path: Optional[str] = None
) -> bool:
    now = time.time()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE devices SET
            last_heartbeat_at = ?,
            status = ?,
            lan_ip = COALESCE(?, lan_ip),
            tailscale_ip = COALESCE(?, tailscale_ip),
            vbox_version = COALESCE(?, vbox_version)
        WHERE device_id = ? AND is_revoked = 0;
        """, (now, status, lan_ip, tailscale_ip, vbox_version, device_id))
        conn.commit()
        return cursor.rowcount > 0


def set_device_status(device_id: str, status: str, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE devices SET status = ? WHERE device_id = ?", (status, device_id))
        conn.commit()
        return cursor.rowcount > 0


def revoke_device(device_id: str, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE devices SET is_revoked = 1, status = 'offline' WHERE device_id = ?", (device_id,))
        conn.commit()
        return cursor.rowcount > 0


# -----------------------------------------------------------------------------
# Published VM Catalog Operations
# -----------------------------------------------------------------------------

def publish_vm(
    vm_id: str,
    device_id: str,
    name: str,
    status: str = "stopped",
    cpu_cores: int = 2,
    ram_mb: float = 2048.0,
    disk_gb: float = 20.0,
    os_type: str = "other",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    now = time.time()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO published_vms (
            vm_id, device_id, name, status, cpu_cores, ram_mb, disk_gb, os_type, is_published, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(vm_id, device_id) DO UPDATE SET
            name = excluded.name,
            status = excluded.status,
            cpu_cores = excluded.cpu_cores,
            ram_mb = excluded.ram_mb,
            disk_gb = excluded.disk_gb,
            os_type = excluded.os_type,
            is_published = 1,
            updated_at = excluded.updated_at;
        """, (vm_id, device_id, name, status, cpu_cores, ram_mb, disk_gb, os_type, now))
        conn.commit()

    return {
        "vm_id": vm_id,
        "device_id": device_id,
        "name": name,
        "status": status,
        "cpu_cores": cpu_cores,
        "ram_mb": ram_mb,
        "disk_gb": disk_gb,
        "os_type": os_type,
        "is_published": 1,
        "updated_at": now
    }


def unpublish_vm(vm_id: str, device_id: str, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE published_vms SET is_published = 0, updated_at = ?
        WHERE vm_id = ? AND device_id = ?;
        """, (time.time(), vm_id, device_id))
        conn.commit()
        return cursor.rowcount > 0


def list_published_vms(device_id: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if device_id:
            cursor.execute("""
            SELECT p.*, d.hostname, d.status as device_status, d.lan_ip, d.owner_name
            FROM published_vms p
            JOIN devices d ON p.device_id = d.device_id
            WHERE p.device_id = ? AND p.is_published = 1 AND d.is_revoked = 0
            ORDER BY p.name ASC;
            """, (device_id,))
        else:
            cursor.execute("""
            SELECT p.*, d.hostname, d.status as device_status, d.lan_ip, d.owner_name
            FROM published_vms p
            JOIN devices d ON p.device_id = d.device_id
            WHERE p.is_published = 1 AND d.is_revoked = 0
            ORDER BY p.name ASC;
            """)
        return [dict(row) for row in cursor.fetchall()]


# -----------------------------------------------------------------------------
# Migration Jobs Operations
# -----------------------------------------------------------------------------

def create_migration_job(
    job_id: str,
    vm_id: str,
    source_device_id: str,
    target_device_id: str,
    plan_id: Optional[str] = None,
    is_same_computer: bool = False,
    start_vm_on_complete: bool = False,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    now = time.time()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO migration_jobs (
            job_id, plan_id, vm_id, source_device_id, target_device_id,
            state, stage, progress_percent, is_same_computer, start_vm_on_complete,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'QUEUED', 'PREFLIGHT', 0.0, ?, ?, ?, ?);
        """, (
            job_id, plan_id or f"plan-{job_id}", vm_id, source_device_id, target_device_id,
            1 if is_same_computer else 0, 1 if start_vm_on_complete else 0, now, now
        ))
        conn.commit()

    return get_migration_job(job_id, db_path=db_path) or {}


def update_migration_job(job_id: str, db_path: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
    if not kwargs:
        return get_migration_job(job_id, db_path=db_path)

    kwargs["updated_at"] = time.time()
    set_clauses = [f"{k} = ?" for k in kwargs.keys()]
    values = list(kwargs.values()) + [job_id]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE migration_jobs SET {', '.join(set_clauses)} WHERE job_id = ?", values)
        conn.commit()

    return get_migration_job(job_id, db_path=db_path)


def get_migration_job(job_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM migration_jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_migration_jobs(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM migration_jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


# -----------------------------------------------------------------------------
# Audit Event Ledger Persistence
# -----------------------------------------------------------------------------

def record_audit_event(
    event_id: str,
    timestamp: float,
    time_iso: str,
    event_type: str,
    message: str,
    vm_id: Optional[str] = None,
    source_node: Optional[str] = None,
    target_node: Optional[str] = None,
    task_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    details_str = json.dumps(details or {})
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO audit_events (
            id, timestamp, time_iso, event_type, vm_id, source_node, target_node, task_id, message, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING;
        """, (event_id, timestamp, time_iso, event_type, vm_id, source_node, target_node, task_id, message, details_str))
        conn.commit()

    return {
        "id": event_id,
        "timestamp": timestamp,
        "time_iso": time_iso,
        "event_type": event_type,
        "message": message,
        "details": details or {}
    }


def list_audit_events(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d.pop("details_json", "{}"))
            except Exception:
                d["details"] = {}
            result.append(d)
        return result


# -----------------------------------------------------------------------------
# Cryptographic Transfer Authorization Operations
# -----------------------------------------------------------------------------

def compute_transfer_hmac(
    token_id: str,
    job_id: str,
    source_device_id: str,
    target_device_id: str,
    artifact_name: str,
    expires_at: float,
    secret_key: Optional[str] = None
) -> str:
    """Computes an HMAC-SHA256 signature binding the token to the specific migration endpoints and artifact."""
    from app.config import settings
    key = (secret_key or settings.GATEWAY_AGENT_TOKEN).encode("utf-8")
    payload = f"{token_id}:{job_id}:{source_device_id}:{target_device_id}:{artifact_name}:{expires_at}"
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_transfer_authorization(
    job_id: str,
    source_device_id: str,
    target_device_id: str,
    artifact_name: str,
    expires_in_seconds: float = 3600.0,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Issues a cryptographically signed, expiring, single-use transfer token scoped to a migration job."""
    now = time.time()
    expires_at = now + expires_in_seconds
    token_id = f"xfer_{secrets.token_hex(16)}"
    sig = compute_transfer_hmac(
        token_id=token_id,
        job_id=job_id,
        source_device_id=source_device_id,
        target_device_id=target_device_id,
        artifact_name=artifact_name,
        expires_at=expires_at
    )
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO transfer_authorizations (
            token_id, job_id, source_device_id, target_device_id,
            artifact_name, hmac_signature, issued_at, expires_at, is_redeemed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0);
        """, (token_id, job_id, source_device_id, target_device_id, artifact_name, sig, now, expires_at))
        conn.commit()

    return {
        "token_id": token_id,
        "job_id": job_id,
        "source_device_id": source_device_id,
        "target_device_id": target_device_id,
        "artifact_name": artifact_name,
        "hmac_signature": sig,
        "issued_at": now,
        "expires_at": expires_at,
        "expires_in_seconds": expires_in_seconds
    }


def verify_and_redeem_transfer_authorization(
    token_id: str,
    job_id: str,
    caller_device_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies HMAC signature, checks expiration, and atomically redeems token (strictly single-use).
    Raises ValueError on invalid signature, expired, or already redeemed token.
    """
    now = time.time()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transfer_authorizations WHERE token_id = ?", (token_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Transfer authorization token '{token_id}' not found.")

        record = dict(row)
        if record["job_id"] != job_id:
            raise ValueError(f"Transfer token is not scoped to migration job '{job_id}'.")

        if caller_device_id and caller_device_id not in (record["source_device_id"], record["target_device_id"]):
            raise ValueError(f"Device '{caller_device_id}' is not authorized to redeem this transfer token.")

        if now > record["expires_at"]:
            raise ValueError("Transfer authorization token has expired.")

        if record["is_redeemed"]:
            raise ValueError("Transfer authorization token has already been redeemed (single-use).")

        expected_sig = compute_transfer_hmac(
            token_id=record["token_id"],
            job_id=record["job_id"],
            source_device_id=record["source_device_id"],
            target_device_id=record["target_device_id"],
            artifact_name=record["artifact_name"],
            expires_at=record["expires_at"]
        )
        if not hmac.compare_digest(record["hmac_signature"], expected_sig):
            raise ValueError("Transfer token HMAC signature validation failed.")

        cursor.execute("""
        UPDATE transfer_authorizations
        SET is_redeemed = 1, redeemed_at = ?
        WHERE token_id = ? AND is_redeemed = 0;
        """, (now, token_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise ValueError("Concurrent redemption detected; token already redeemed.")

        record["is_redeemed"] = 1
        record["redeemed_at"] = now
        return record
