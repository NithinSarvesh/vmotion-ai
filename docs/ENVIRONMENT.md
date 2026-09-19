# VMotion AI — Authoritative Environment Specification

## Authoritative Python Environment

All backend execution, testing, machine learning training, and inference for VMotion AI are pinned to a single authoritative Python environment:

- **Python Version**: `Python 3.11.9 (64-bit)`
- **Environment Path**: `d:\projects\vmotion ai\.venv`
- **Core Dependencies**:
  - `fastapi == 0.141.1`
  - `pydantic == 2.13.5` / `pydantic-settings == 2.15.0`
  - `uvicorn == 0.53.0`
  - `torch == 2.14.0` (Native Windows 64-bit precompiled wheels)
  - `gymnasium == 1.3.0`
  - `stable-baselines3 == 2.9.0`
  - `sb3-contrib == 2.9.0`
  - `numpy == 2.4.6`
  - `pytest == 9.1.1` / `pytest-asyncio == 1.4.0`

---

## Why Python 3.11?

Python 3.14 was recently released and lacks precompiled C-extension wheel binary distributions for several deep reinforcement learning dependencies (`torch`, `sb3-contrib`). Python 3.11.9 provides certified, stable, precompiled wheel support across all PyTorch and Farama Foundation RL packages on Windows.

---

## Canonical Execution Commands

From the workspace root (`d:\projects\vmotion ai`):

### 1. Automated Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v backend/tests
```

### 2. Run Backend Control Plane
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Run Policy Evaluation
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m app.training.evaluate --episodes-per-scenario 15 --model-path models/ppo_vmotion_v4_masked.zip --output-json evaluation_results.json --output-report docs/PPO_EVALUATION_REPORT.md
```

### 4. Run RL Policy Training
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m app.training.train --timesteps 50000 --seed 42
```

### 5. Frontend Development & Production Build
```powershell
cd frontend
npm install
npm run build
```
