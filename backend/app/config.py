"""
VMotion AI Configuration Module.
Strict adherence to safety gates, human-in-the-loop controls, and provider abstractions.
"""
from typing import Literal
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
    VBOX_DEMO_VM_NAME: str = "DemoVM"
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
    
    @model_validator(mode="after")
    def sync_agent_tokens(self) -> "Settings":
        """
        Synchronize GATEWAY_AGENT_TOKEN and VBOX_AGENT_SECRET.
        Ensures that if Render defines GATEWAY_AGENT_TOKEN dynamically,
        VBOX_AGENT_SECRET matches it unless explicitly configured otherwise.
        """
        if self.GATEWAY_AGENT_TOKEN != "vmotion-vbox-secret" and self.VBOX_AGENT_SECRET == "vmotion-vbox-secret":
            self.VBOX_AGENT_SECRET = self.GATEWAY_AGENT_TOKEN
        elif self.VBOX_AGENT_SECRET != "vmotion-vbox-secret" and self.GATEWAY_AGENT_TOKEN == "vmotion-vbox-secret":
            self.GATEWAY_AGENT_TOKEN = self.VBOX_AGENT_SECRET
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
