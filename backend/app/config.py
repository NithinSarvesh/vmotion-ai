"""
VMotion AI Configuration Module.
Strict adherence to safety gates, human-in-the-loop controls, and provider abstractions.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "VMotion AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Operational Mode: 'live' or 'simulation'
    MODE: Literal["live", "simulation"] = "simulation"
    
    # Provider Selection: 'simulation', 'proxmox', 'libvirt'
    PROVIDER_TYPE: Literal["simulation", "proxmox", "libvirt"] = "simulation"
    
    # Safety & Governance Gates
    ENABLE_HUMAN_APPROVAL: bool = True       # Mandatory: AI cannot execute without human approval
    ENABLE_AUTONOMOUS_MODE: bool = False     # Strictly false by default
    
    # Proxmox VE Connection Parameters
    PROXMOX_ENDPOINT: str = "https://192.168.1.100:8006/api2/json"
    PROXMOX_USER: str = "root@pam"
    PROXMOX_TOKEN_ID: str = "vmotion"
    PROXMOX_TOKEN_SECRET: str = ""
    PROXMOX_VERIFY_SSL: bool = False
    
    # Libvirt / KVM Connection Parameters
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
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
