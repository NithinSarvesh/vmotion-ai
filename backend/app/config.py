"""
VMotion AI Configuration Module.
Strict adherence to safety gates, human-in-the-loop controls, and provider abstractions.
"""
from typing import Literal, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "VMotion AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Operational Mode: 'live' or 'simulation'
    MODE: Literal["live", "simulation"] = "simulation"
    
    # Provider Selection: 'simulation', 'virtualbox', 'proxmox', 'libvirt'
    PROVIDER_TYPE: Literal["simulation", "virtualbox", "proxmox", "libvirt"] = "simulation"
    
    # Safety & Governance Gates
    ENABLE_HUMAN_APPROVAL: bool = True       # Mandatory: AI cannot execute without human approval
    ENABLE_AUTONOMOUS_MODE: bool = False     # Strictly false by default
    
    # Oracle VirtualBox Migration Parameters (Cold OVA & Legacy Teleport)
    VBOX_MIGRATION_MODE: Literal["cold_ova", "teleport"] = "cold_ova"
    VBOX_MANAGE_PATH: str = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
    VBOX_HOST_A_URL: str = "http://127.0.0.1:8001"
    VBOX_HOST_B_URL: str = "http://192.168.1.101:8001"
    VBOX_AGENT_SECRET: str = "vmotion-vbox-secret"
    VBOX_TELEPORT_PORT: int = 60050
    VBOX_SHARED_STORAGE_PATH: str = r"C:\VMotionShared"
    VBOX_STAGING_PATH: str = r"C:\VMotionStaging"
    VBOX_DEMO_VM_NAME: str = "VMotion-Demo"
    VBOX_TARGET_VM_NAME: str = "VMotion - demo target"

    # Optional Legacy Parameters
    PROXMOX_ENDPOINT: str = "https://192.168.1.100:8006/api2/json"
    PROXMOX_USER: str = "root@pam"
    PROXMOX_TOKEN_ID: str = "vmotion"
    PROXMOX_TOKEN_SECRET: str = ""
    PROXMOX_VERIFY_SSL: bool = False
    LIBVIRT_URI: str = "qemu+ssh://root@192.168.1.100/system"
    
    # Safety Gate Deterministic Thresholds
    SAFETY_MAX_CPU_PERCENT: float = 85.0
    SAFETY_MAX_RAM_PERCENT: float = 90.0
    SAFETY_COOLDOWN_SECONDS: int = 60
    SAFETY_REQUIRE_STORAGE_SHARED: bool = True
    SAFETY_REQUIRE_CLUSTER_QUORUM: bool = True
    
    # Telemetry Polling Intervals (seconds)
    TELEMETRY_INTERVAL_SECONDS: float = 2.0

    # Operator Authentication Key for Control Plane Configuration Updates
    OPERATOR_API_KEY: str = "vmotion-operator-key-default"
    
    # Cloud Agent Gateway Parameters (WSS Outbound Agents)
    GATEWAY_AGENT_TOKEN: str = "vmotion-vbox-secret"
    AGENT_HEARTBEAT_TIMEOUT_SECONDS: float = 10.0
    CORS_ORIGINS: str = "*"
    SERVE_FRONTEND: bool = True
    HOST_A_ID: str = "vbox-host-a"
    HOST_B_ID: str = "vbox-host-b"

    # Database Persistence
    DATABASE_PATH: str = "vmotion.db"

    # Device Enrollment & Registration
    ENROLLMENT_SECRET: str = "vmotion-enroll-key"

    # Agent Packaging & Distribution
    AGENT_DIST_DIR: str = "dist"
    AGENT_BINARY_NAME: str = "vmotion-agent.exe"

    # S3-Compatible Object Storage Fallback (Optional Cross-Network Transfer)
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"
    
    # Environment: 'development', 'test', 'production'
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    
    @model_validator(mode="after")
    def validate_production_and_sync_tokens(self) -> "Settings":
        """
        Validates security requirements in production and synchronizes gateway tokens.
        In production (or Render environments), fails closed if insecure default secrets
        remain configured or if debug mode is active.
        """
        import os
        is_prod = (
            self.ENVIRONMENT == "production"
            or os.getenv("RENDER") is not None
            or os.getenv("ENVIRONMENT") == "production"
        )

        # Synchronize GATEWAY_AGENT_TOKEN and VBOX_AGENT_SECRET
        if self.GATEWAY_AGENT_TOKEN != "vmotion-vbox-secret" and self.VBOX_AGENT_SECRET == "vmotion-vbox-secret":
            self.VBOX_AGENT_SECRET = self.GATEWAY_AGENT_TOKEN
        elif self.VBOX_AGENT_SECRET != "vmotion-vbox-secret" and self.GATEWAY_AGENT_TOKEN == "vmotion-vbox-secret":
            self.GATEWAY_AGENT_TOKEN = self.VBOX_AGENT_SECRET

        if is_prod:
            if self.DEBUG:
                raise ValueError("Production security violation: DEBUG mode must be disabled in production.")
            if self.OPERATOR_API_KEY == "vmotion-operator-key-default":
                raise ValueError("Production security violation: OPERATOR_API_KEY must not use default placeholder.")
            if self.ENROLLMENT_SECRET == "vmotion-enroll-key":
                raise ValueError("Production security violation: ENROLLMENT_SECRET must not use default placeholder.")
            if self.GATEWAY_AGENT_TOKEN == "vmotion-vbox-secret":
                raise ValueError("Production security violation: GATEWAY_AGENT_TOKEN must not use default placeholder.")
            if self.VBOX_AGENT_SECRET == "vmotion-vbox-secret":
                raise ValueError("Production security violation: VBOX_AGENT_SECRET must not use default placeholder.")
            if self.PROVIDER_TYPE != "virtualbox":
                raise ValueError("Production security violation: Deployed provider in production must be 'virtualbox'.")
            if self.VBOX_MIGRATION_MODE != "cold_ova":
                raise ValueError("Production security violation: Deployed VirtualBox provider must use 'cold_ova' migration mode.")

        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
