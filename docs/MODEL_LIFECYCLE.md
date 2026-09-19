# VMotion AI — Reinforcement Learning Model Lifecycle & Governance

## 1. Action Space Semantics & Architectural Coupling

The VMotion AI policy architecture decouples workload selection from destination placement:

$$\text{Telemetry} \longrightarrow \text{103 Normalized Features} \longrightarrow \text{PPO Workload Selection (Discrete 7)} \longrightarrow \text{Constraint-Aware Destination Selector} \longrightarrow \text{Deterministic Safety Gate}$$

### 1.1 Action Space Definition
- **Space**: `gymnasium.spaces.Discrete(7)`
- **Action 0**: **No-Op**. The agent elects not to initiate any migration during the current evaluation interval.
- **Actions 1..6**: **Workload Selection**. Specifies VM index 0 through 5 (in deterministic alphanumeric sorted order) to migrate.

### 1.2 Destination Selection Coupling
> [!IMPORTANT]
> **Destination selection is NOT chosen by the PPO policy.**  
> Destination selection is executed by a separate, deterministic, constraint-aware destination selector:
> ```python
> candidate_nodes = [
>     n for n in cluster.nodes.values()
>     if n.name != source_node.name
>     and n.status == 'online'
>     and (n.ram_total_gb - n.ram_used_gb) >= vm.ram_allocated_gb
> ]
> destination_node = min(candidate_nodes, key=lambda n: n.cpu_percent)
> ```

### 1.3 Pre-Dispatch Deterministic Safety Gate
Before any migration proposal can transition to `PENDING_APPROVAL`, it must pass the deterministic safety gate:
- Saturated CPU destination projection check
- Insufficient RAM rejection
- Active per-VM and per-host cooldown timer enforcement
- Clustered quorum and shared storage accessibility verification
- Running workload state verification

---

## 2. Model Versioning & Contract Schema

Every model checkpoint trained for VMotion AI adheres to semantic versioning contracts defined in `app/adapter/contracts.py`:
- `OBSERVATION_SCHEMA_VERSION = "v1.0.0"` (103 continuous features in `[-1.0, 1.0]`)
- `ACTION_SCHEMA_VERSION = "v1.0.0"` (`Discrete(7)`)
- `MODEL_SCHEMA_VERSION = "v1.0.0"`

Companion metadata files (`.meta.json`) store:
- Model SHA-256 checksum
- Hyperparameters (`learning_rate`, `batch_size`, `gamma`, `n_steps`, `gae_lambda`, `clip_range`, `ent_coef`)
- Training timesteps and evaluation history

---

## 3. Benchmarking Protocol & Acceptance Criteria

To prevent premature claims of policy performance, all models are evaluated against the authoritative **10-scenario benchmark suite**:

### 3.1 Scenario Splits
- **TRAIN Split**: `NORMAL`, `CPU_HOTSPOT`, `RAM_HOTSPOT`, `MIXED_OVERLOAD`
- **VALIDATION Split**: `SLA_CRITICAL`, `UNEVEN_CLUSTER`, `RAPID_LOAD_CHANGE`
- **UNSEEN TEST Split**: `NETWORK_HOTSPOT`, `EXPENSIVE_MIGRATION`, `MIGRATION_COOLDOWN_PRESSURE`

### 3.2 Evaluation Command
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m app.training.evaluate --episodes-per-scenario 15 --model-path models/ppo_vmotion_v4_masked.zip --output-json evaluation_results.json --output-report docs/PPO_EVALUATION_REPORT.md
```

### 3.3 Acceptance Criteria for Model Promotion
A PPO checkpoint may only be designated as the primary decision engine if:
1. Mean reward on the **UNSEEN TEST Split** strictly exceeds the Baseline Rule Heuristic.
2. 95% Confidence Interval lower bound on reward is non-overlapping or superior to baseline.
3. Overload steps per episode do not exceed baseline heuristic by more than 5%.
4. Zero unmasked invalid action violations occur during evaluation.

---

## 4. Authoritative Fallback Governance

When a trained PPO model does not meet the acceptance criteria (as confirmed with `ppo_vmotion_v4_masked.zip`), VMotion AI operates with the **Calibrated Baseline Rule Heuristic** as its primary authoritative decision engine.

The PPO model is retained in shadow/evaluation mode, enabling:
- Real-time inference latency tracking
- Comparative telemetry observation
- Diagnostic action mask inspection
- Safe, non-destructive RL iteration
