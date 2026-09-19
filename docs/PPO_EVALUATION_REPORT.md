# VMotion AI — Phase 4: PPO Policy Performance Validation Report

**Date**: 2026-09-19 06:03:32 UTC  
**Checkpoint Evaluated**: `models/ppo_vmotion_v4_masked.zip`  
**Artifact SHA-256**: `450d406ddb4c3e4ab68423f00478825310069756f8c2aceda79627de0d2d8747`  
**Schema Contract**: Observation `v1.0.0` (103-dim), Action `v1.0.0` (Discrete(7))  
**Episodes per Scenario**: 15 (Total Benchmark Episodes: 450)  

---

## 1. Action Space Semantics & Architectural Coupling

The VMotion AI policy architecture is structured as follows:

$$\text{Telemetry} \longrightarrow \text{103 Normalized Features} \longrightarrow \text{PPO Workload Selection (Discrete 7)} \longrightarrow \text{Constraint-Aware Destination Selector} \longrightarrow \text{Deterministic Safety Gate}$$

- **PPO Action Space**: `Discrete(7)`
  - `0`: **No-Op** (maintain current cluster placement).
  - `1..6`: **Workload Selection** (specifies VM index 0 to 5 in alphanumeric sorted order to migrate).
- **Destination Selection**: **Destination selection is NOT chosen by PPO.** It is executed by a deterministic, constraint-aware selector that chooses the least-loaded alternative online node with sufficient RAM capacity (`min(candidates, key=lambda n: n.cpu_percent)`).
- **Deterministic Safety Gate**: Validates all pre-conditions (cooldown, storage accessibility, quorum, RAM headroom, CPU overload projections) before dispatch.

---

## 2. Executive Summary: Does PPO Outperform Baseline?

| Evaluation Dataset | Baseline Heuristic (Mean Reward) | Trained MaskablePPO (Mean Reward) | Delta | PPO Superior? |
| :--- | :--- | :--- | :--- | :--- |
| **Overall (10 Scenarios)** | **106.91** $\pm$ 187.09 | **-263.48** $\pm$ 252.7 | -370.39 | **NO (Baseline Superior)** |
| **TRAIN Split (4 Scenarios)** | 44.83 | -353.64 | -398.47 | **NO** |
| **VALIDATION Split (3 Scenarios)** | 52.39 | -353.58 | -405.97 | **NO** |
| **UNSEEN TEST Split (3 Scenarios)** | **244.19** | **-53.16** | -297.35 | **NO (Baseline Superior)** |

> [!IMPORTANT]
> **Empirical Conclusion**: On the UNSEEN TEST set, the calibrated baseline heuristic achieves a mean reward of **244.19**, while the trained MaskablePPO checkpoint achieves **-53.16**. The baseline heuristic outperforms the current PPO checkpoint.

---

## 3. Overall Multi-Policy Comparison (Aggregate Across All 10 Scenarios)

| Metric | Baseline Rule Heuristic | Random Valid Masked Policy | Trained MaskablePPO (`v4_masked`) |
| :--- | :--- | :--- | :--- |
| **Mean Reward** | **106.91** | -89.25 | **-263.48** |
| **Std Deviation** | 187.09 | 207.59 | 252.7 |
| **Median Reward** | 203.54 | 2.47 | -114.3 |
| **Min / Max Reward** | [-277.51, 278.37] | [-486.42, 110.44] | [-686.47, -6.23] |
| **95% Confidence Interval** | [-26.92, 240.74] | [-237.74, 59.24] | [-444.23, -82.72] |
| **Mean Migrations / Ep** | 12.75 | 73.11 | 0.0 |
| **Mean No-Ops / Ep** | 87.25 | 26.89 | 100.0 |
| **Mean SLA Breaches / Ep** | 77.32 | 77.32 | 77.32 |
| **Mean Overload Steps / Ep** | 6.53 | 16.93 | 60.22 |
| **Final Jain's Fairness** | **0.9605** | 0.8944 | **0.7682** |

---

## 4. Reward Decomposition Breakdown

Why did each policy achieve its reward score? Below is the average contribution of each scalar term across episodes:

| Reward Component | Baseline Rule Heuristic | Random Valid Policy | Trained MaskablePPO |
| :--- | :--- | :--- | :--- |
| Fairness Reward (+2.5 * Jain's) | 241.66 | 221.28 | 184.53 |
| CPU Imbalance Penalty (-1.5 * std) | -12.78 | -25.87 | -44.0 |
| Stability Bonus (+1.0 on balanced No-Op) | 69.89 | 8.48 | 1.97 |
| SLA Breach Penalty (-2.0 / breach) | -154.64 | -154.64 | -154.64 |
| Host Overload Penalty (-4.0 / overloaded host) | -26.43 | -74.72 | -251.34 |
| Migration Transient Cost (-0.8 or -1.5 / mig) | -10.8 | -63.79 | 0.0 |
| Invalid Action Penalty (-10.0 / invalid) | 0.0 | 0.0 | 0.0 |

---

## 5. Scenario-Level Performance Matrix

| Scenario | Split | Baseline Mean Reward | PPO Mean Reward | Baseline Migrations | PPO Migrations | Baseline SLA Breaches | PPO SLA Breaches |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `NORMAL` | **TRAIN** | 212.6 | -85.99 | 8.27 | 0.0 | 50.33 | 50.33 |
| `CPU_HOTSPOT` | **TRAIN** | 44.77 | -499.49 | 12.2 | 0.0 | 112.47 | 112.47 |
| `RAM_HOTSPOT` | **TRAIN** | 199.47 | -142.61 | 2.93 | 0.0 | 40.87 | 40.87 |
| `NETWORK_HOTSPOT` | **UNSEEN TEST** | 278.37 | -6.23 | 8.93 | 0.0 | 15.47 | 15.47 |
| `SLA_CRITICAL` | **VALIDATION** | -167.06 | -573.2 | 25.47 | 0.0 | 172.07 | 172.07 |
| `MIXED_OVERLOAD` | **TRAIN** | -277.51 | -686.47 | 28.33 | 0.0 | 183.0 | 183.0 |
| `EXPENSIVE_MIGRATION` | **UNSEEN TEST** | 221.08 | -85.76 | 8.53 | 0.0 | 42.8 | 42.8 |
| `UNEVEN_CLUSTER` | **VALIDATION** | 207.61 | -418.53 | 9.47 | 0.0 | 43.53 | 43.53 |
| `RAPID_LOAD_CHANGE` | **VALIDATION** | 116.63 | -69.0 | 18.0 | 0.0 | 68.27 | 68.27 |
| `MIGRATION_COOLDOWN_PRESSURE` | **UNSEEN TEST** | 233.13 | -67.48 | 5.33 | 0.0 | 44.4 | 44.4 |

---

## 6. Empirical Failure Mode Analysis

Detailed inspection of the benchmark traces reveals specific behavioral patterns:

### 1. Excessive No-Op Bias (Conservative Inaction)
- **Observation**: Across all scenarios, the trained MaskablePPO policy executed approximately `0.0` migrations per episode (No-Op rate $\approx 100\%$).
- **Root Cause**: During early reinforcement learning exploration, triggering an invalid action or moving a VM incurs immediate penalties ($-10.0$ for invalid, $-0.8$ for migration, cooldown locks). The policy discovered a local optimum: selecting action `0` (No-Op) guarantees zero migration penalties and zero invalid penalties.
- **Consequence**: In heavily loaded scenarios like `CPU_HOTSPOT`, `MIXED_OVERLOAD`, and `UNEVEN_CLUSTER`, the policy remains idle, enduring persistent host overload penalties ($-4.0$ per host per step $\times 100$ steps $= -400.0$ to $-800.0$).

### 2. Hotspot Inaction
- In `CPU_HOTSPOT` and `UNEVEN_CLUSTER`, Node 01 is severely saturated (>90% CPU). The baseline rule heuristic actively triggers 8–12 migrations to distribute workloads to idle nodes, bringing Jain's fairness to >0.96 and eliminating the overload penalty.
- PPO fails to take action, resulting in a final Jain's fairness index of ~0.76 and high SLA breaches.

### 3. Diagnosis: Why Baseline Outperforms Current PPO Checkpoint
1. **Training Timesteps**: 25,000 steps represents only ~12 policy rollouts. MaskablePPO has not yet navigated past the conservative local minimum.
2. **Overload Penalty Visibility**: While host overload penalty is $-4.0$, immediate migration cost is $-0.8$. Because overload penalty accumulates over time, an agent with $\gamma = 0.99$ requires more training iterations or value function warmth to realize that paying $-0.8$ immediately saves hundreds of penalty points over future steps.
3. **Safe Baseline Fallback Justified**: These empirical results validate the architectural decision in VMotion AI to **strictly maintain the calibrated baseline rule heuristic as an authoritative fallback**. When PPO is suboptimal or inactive, the control plane relies on the rule engine.

---

## 7. Operational Recommendation for Next Steps

1. **Preserve Truthful Reporting**: The control plane frontend must display the exact measured status and performance without claiming PPO superiority.
2. **Targeted RL Improvements (Future Phase)**:
   - Increase training timesteps with curriculum learning starting from unbalanced topologies (`UNEVEN_CLUSTER`, `CPU_HOTSPOT`).
   - Consider value-head initialization or behavioral cloning from the baseline heuristic.
   - Fine-tune entropy coefficient and credit assignment for long-horizon overload relief.