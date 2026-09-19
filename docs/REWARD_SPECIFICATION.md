# VMotion AI — Reinforcement Learning Reward Specification

This document provides the exact mathematical formulation, penalty weights, and step-by-step accounting for the reinforcement learning objective in VMotion AI.

---

## 1. Per-Step Reward Formulation

At each simulated timestep $t$, the scalar reward $R_t$ is computed as:

$$R_t = R_{\text{balance}} + R_{\text{stability}} - P_{\text{SLA}} - P_{\text{overload}} - P_{\text{migration}} - P_{\text{invalid}}$$

---

## 2. Component Mathematical Definitions

### 1. Load Balance & Fairness Dividend ($R_{\text{balance}}$)
Measures cluster compute uniformity across all $N=3$ compute hosts:

$$R_{\text{balance}} = 2.5 \cdot \mathcal{J}_{\text{cpu}} - 1.5 \cdot \sigma_{\text{cpu}}$$

where:
- $\mathcal{J}_{\text{cpu}} = \frac{\left(\sum_{i=1}^N u_i\right)^2}{N \sum_{i=1}^N u_i^2}$ is **Jain's Fairness Index** across normalized node CPU utilizations $u_i \in [0.0, 1.0]$.
- $\sigma_{\text{cpu}} = \sqrt{\frac{1}{N}\sum_{i=1}^N (u_i - \bar{u})^2}$ is the standard deviation of node CPU utilization.
- Range: Under ideal balance ($\mathcal{J} = 1.0, \sigma = 0.0$), $R_{\text{balance}} = +2.50$ per step.

### 2. Equilibrium Stability Bonus ($R_{\text{stability}}$)
Rewards the policy for refraining from unnecessary migrations when the cluster is already in nominal balance:

$$R_{\text{stability}} = 
\begin{cases}
+1.0 & \text{if } a_t = 0 \text{ (No-Op) and } \sigma_{\text{cpu}} < 0.12 \\
0.0 & \text{otherwise}
\end{cases}$$

### 3. Workload SLA Breach Penalty ($P_{\text{SLA}}$)
Penalizes workload CPU saturation above contractual thresholds:

$$P_{\text{SLA}} = 2.0 \times \sum_{j=1}^M \mathbb{I}[u_{\text{vm}, j} > \tau_{\text{SLA}, j}]$$

where:
- $M = 6$ active workloads.
- $\tau_{\text{SLA}, j}$ is the workload SLA ceiling (e.g. 80% for high priority, 85% for critical).
- Each breached workload deducts $2.0$ points per step.

### 4. Compute Node Overload Penalty ($P_{\text{overload}}$)
Prevents hypervisor exhaustion and CPU throttling:

$$P_{\text{overload}} = 4.0 \times \sum_{i=1}^N \mathbb{I}[u_{\text{node}, i} > 0.85]$$

- Any host operating above 85% CPU capacity incurs a strict $-4.0$ penalty per step.

### 5. Live Migration Overhead ($P_{\text{migration}}$)
Penalizes the operational cost, memory dirtying, and network interconnect traffic of active migrations:

$$P_{\text{migration}} = 
\begin{cases}
0.8 & \text{if } a_t \in \{1..6\} \text{ (Migration executed)} \\
0.0 & \text{if } a_t = 0 \text{ (No-Op)}
\end{cases}$$

### 6. Invalid Action / Cooldown Violation Penalty ($P_{\text{invalid}}$)
Penalizes attempts to execute an invalid action (e.g. migrating a VM in cooldown or selecting a target without capacity):

$$P_{\text{invalid}} = 
\begin{cases}
10.0 & \text{if } \text{action is masked or destination has insufficient RAM} \\
0.0 & \text{otherwise}
\end{cases}$$

---

## 3. Cumulative Episode Trajectory & Benchmark Accounting

Over a standard evaluation episode of $T = 100$ steps:
- **Baseline Rule Heuristic**: Rebalances heavily skewed workloads within the first 8–15 steps, incurring small migration overheads ($\approx 10 \times 0.8 = 8.0$), then settles into nominal equilibrium ($\sigma_{\text{cpu}} < 0.10, \mathcal{J} > 0.96$) collecting steady $+3.3$ to $+3.5$ points per step while minimizing SLA breaches.
- **Random Masked Policy**: Continuously triggers migrations at nearly every step ($\approx 70\text{--}80$ migrations), repeatedly destabilizing nodes, incurring heavy migration penalties and SLA contention, yielding scores near zero or negative.
- **Trained MaskablePPO**: Optimizes for timing interventions precisely when thermal imbalance crosses the rebalancing dividend threshold ($\Delta \sigma > 0.15$), maximizing cumulative reward over the full horizon.
