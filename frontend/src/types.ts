export interface NodeTelemetry {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'degraded';
  cpu_cores: number;
  cpu_percent: number;
  ram_total_mb: number;
  ram_used_mb: number;
  ram_percent: number;
  net_rx_kbps: number;
  net_tx_kbps: number;
  disk_total_gb: number;
  disk_used_gb: number;
  shared_storage_accessible: boolean;
  quorum_healthy: boolean;
  active_vms: string[];
}

export interface VMTelemetry {
  vmid: string;
  name: string;
  node_id: string;
  status: 'running' | 'stopped' | 'paused' | 'migrating';
  cpu_cores: number;
  cpu_percent: number;
  ram_allocated_mb: number;
  ram_used_mb: number;
  ram_percent: number;
  net_io_kbps: number;
  disk_allocated_gb: number;
  sla_priority: 'critical' | 'high' | 'standard' | 'batch';
  sla_max_cpu_percent: number;
  last_migrated_at: number | null;
  migration_count: number;
  uptime_seconds: number;
}

export interface ClusterState {
  is_live: boolean;
  connected: boolean;
  provider_name: string;
  timestamp: number;
  nodes: Record<string, NodeTelemetry>;
  vms: Record<string, VMTelemetry>;
  error_message?: string | null;
}

export interface SafetyCheckResult {
  check_name: string;
  passed: boolean;
  severity: 'CRITICAL' | 'WARNING';
  message: string;
  metric_value?: string;
}

export interface SafetyEvaluation {
  vm_id: string;
  source_node: string;
  target_node: string;
  passed: boolean;
  blocked: boolean;
  total_checks: number;
  passed_checks: number;
  evaluated_at: number;
  results: SafetyCheckResult[];
  rejection_reasons: string[];
}

export interface Recommendation {
  action_type: 'MIGRATE' | 'NO_OP';
  vm_id?: string;
  vm_name?: string;
  source_node?: string;
  target_node?: string;
  reason: string;
  engine_type: 'PPO_POLICY' | 'BASELINE_RULE' | 'NO_OP';
  confidence_score: number;
  expected_load_balance_improvement: number;
  action_index: number;
  timestamp: number;
  metrics_summary: Record<string, any>;
}

export type ProposalStatus =
  | 'RECOMMENDED'
  | 'SAFETY_CHECK'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'DISPATCHED'
  | 'TASK_RUNNING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'REJECTED'
  | 'BLOCKED'
  | 'FAILED'
  | 'CANCELLED';

export interface PendingProposal {
  proposal_id: string;
  vm_id: string;
  vm_name: string;
  source_node: string;
  target_node: string;
  reason: string;
  engine_type: string;
  confidence_score: number;
  safety_evaluation: SafetyEvaluation;
  status: ProposalStatus;
  created_at: number;
  approved_at?: number;
  rejected_at?: number;
  rejection_reason?: string;
  cancelled_at?: number;
  cancellation_reason?: string;
  task_id?: string;
}

export type MigrationState =
  | 'PREPARING'
  | 'VALIDATING'
  | 'MIGRATING'
  | 'MONITORING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'FAILED'
  | 'BLOCKED';

export interface MigrationTaskStatus {
  task_id: string;
  plan_id: string;
  vm_id: string;
  source_node: string;
  target_node: string;
  state: MigrationState;
  progress_percent: number;
  started_at: number;
  updated_at: number;
  completed_at?: number;
  verified_at?: number;
  error?: string;
  verification_details?: Record<string, any>;
}

export interface AuditEntry {
  id: string;
  timestamp: number;
  time_iso: string;
  event_type: string;
  vm_id?: string;
  source_node?: string;
  target_node?: string;
  task_id?: string;
  message: string;
  details: Record<string, any>;
}

export interface MetricHistoryPoint {
  timestamp: number;
  value: number;
}

export interface NodeTelemetryProfile {
  node_id: string;
  current_cpu_percent: number;
  cpu_moving_avg: number;
  cpu_trend: 'rising' | 'falling' | 'stable';
  current_ram_percent: number;
  ram_available_mb: number;
  net_throughput_kbps: number;
  hosted_vm_count: number;
  cpu_history: MetricHistoryPoint[];
}

export interface VMTelemetryProfile {
  vm_id: string;
  name: string;
  node_id: string;
  status: string;
  current_cpu_percent: number;
  cpu_moving_avg: number;
  ram_allocated_mb: number;
  ram_used_mb: number;
  sla_priority: string;
  sla_max_cpu_percent: number;
  is_sla_breached: boolean;
  sla_breach_count: number;
  last_migrated_at: number | null;
  migration_count: number;
  cpu_history: MetricHistoryPoint[];
}

export interface AggregatedClusterTelemetry {
  timestamp: number;
  provider_name: string;
  is_live: boolean;
  connected: boolean;
  total_cpu_cores: number;
  avg_cluster_cpu_percent: number;
  cluster_cpu_imbalance_std: number;
  jains_fairness_cpu: number;
  total_ram_total_gb: number;
  total_ram_used_gb: number;
  active_vm_count: number;
  migrating_vm_count: number;
  total_sla_breaches: number;
  node_profiles: Record<string, NodeTelemetryProfile>;
  vm_profiles: Record<string, VMTelemetryProfile>;
}

export interface PPOModelHealth {
  model_loaded: boolean;
  model_path: string;
  health_state?: string;
  status_message: string;
  file_exists: boolean;
  sha256_checksum: string | null;
  observation_dimension: number;
  action_space_size: number;
  observation_schema_version?: string;
  action_schema_version?: string;
  model_version?: string;
  framework: string;
  baseline_fallback_active: boolean;
  baseline_policy_reward_expected: number;
  active_policy: string;
  last_inference_latency_ms?: number;
}

export interface TelemetryPulsePayload {
  type: 'TELEMETRY_PULSE';
  timestamp: number;
  cluster: ClusterState;
  telemetry?: AggregatedClusterTelemetry;
  model_health?: PPOModelHealth;
  recommendation: Recommendation | null;
  safety_evaluation: SafetyEvaluation | null;
  proposals: PendingProposal[];
  active_tasks: MigrationTaskStatus[];
  completed_tasks: MigrationTaskStatus[];
  audit_entries: AuditEntry[];
}

export type ConnectionStatus = 'CONNECTED' | 'AUTHENTICATION_ERROR' | 'DISCONNECTED' | 'UNAVAILABLE';

export interface ProviderConnectionResult {
  provider: 'simulation' | 'proxmox' | 'libvirt';
  status: ConnectionStatus;
  latency_ms?: number | null;
  hypervisor_version?: string | null;
  node_count: number;
  vm_count: number;
  message: string;
  details?: Record<string, any> | null;
}

export interface ClusterConfig {
  provider_type: 'simulation' | 'proxmox' | 'libvirt';
  is_live: boolean;
  proxmox: {
    endpoint: string;
    user: string;
    token_id: string;
    token_secret_configured: boolean;
    verify_ssl: boolean;
  };
  libvirt: {
    uri: string;
  };
}
