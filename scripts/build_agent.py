"""
VMotion AI - Windows Agent Packaging Utility.
Compiles vmotion-agent/agent.py into a standalone single-file Windows executable (dist/vmotion-agent.exe).
"""
import os
import sys
import shutil
import hashlib
import subprocess
from pathlib import Path


def build_agent():
    repo_root = Path(__file__).resolve().parent.parent
    agent_script = repo_root / "vmotion-agent" / "agent.py"
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build"

    if not agent_script.exists():
        print(f"[ERROR] Agent script not found at {agent_script}")
        sys.exit(1)

    print("===================================================================")
    print(" VMotion AI - Building Standalone Windows Host Agent (.exe)")
    print("===================================================================")
    print(f"Target Script:  {agent_script}")
    print(f"Output Path:    {dist_dir / 'vmotion-agent.exe'}")
    print("-------------------------------------------------------------------")

    dist_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name", "vmotion-agent",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(repo_root),
        "--hidden-import", "uvicorn",
        "--hidden-import", "websockets",
        "--hidden-import", "pydantic",
        "--hidden-import", "psutil",
        "--hidden-import", "starlette",
        "--hidden-import", "fastapi",
        "--clean",
        "--noconfirm",
        str(agent_script)
    ]

    print(f"Executing: {' '.join(cmd)}")
    rc = subprocess.call(cmd, cwd=str(repo_root))

    target_exe = dist_dir / "vmotion-agent.exe"
    if rc != 0 or not target_exe.exists():
        print(f"\n[FAILURE] Build failed with return code {rc}")
        sys.exit(rc or 1)

    file_size_mb = round(target_exe.stat().st_size / (1024 * 1024), 2)
    hasher = hashlib.sha256()
    with open(target_exe, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()

    print("\n===================================================================")
    print(" BUILD SUCCESSFUL!")
    print(f" Executable:  {target_exe}")
    print(f" Size:        {file_size_mb} MB")
    print(f" SHA-256:     {digest}")
    print("===================================================================")


if __name__ == "__main__":
    build_agent()
