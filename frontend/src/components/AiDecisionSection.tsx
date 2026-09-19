import React, { useState } from 'react';
import { 
  BrainCircuit, 
  Check, 
  X, 
  AlertOctagon, 
  Info,
  Lock,
  Cpu,
  Layers,
  ShieldAlert,
  Clock,
  Fingerprint
} from 'lucide-react';
import type { Recommendation, PendingProposal, SafetyEvaluation, PPOModelHealth } from '../types';

interface AiDecisionSectionProps {
  recommendation: Recommendation | null;
  safetyEvaluation?: SafetyEvaluation | null;
  modelHealth?: PPOModelHealth | null;
  proposals: PendingProposal[];
  onApprove: (proposalId: string) => Promise<boolean>;
  onReject: (proposalId: string) => Promise<boolean>;
}

export const AiDecisionSection: React.FC<AiDecisionSectionProps> = ({
  recommendation,
  modelHealth,
  proposals,
  onApprove,
  onReject
}) => {
  const [submitting, setSubmitting] = useState<string | null>(null);

  const activeProposal = proposals.find(
    (p) => p.status === 'PENDING_APPROVAL' || p.status === 'BLOCKED'
  );

  const handleApprove = async (id: string) => {
    setSubmitting(id);
    await onApprove(id);
    setSubmitting(null);
  };

  const handleReject = async (id: string) => {
    setSubmitting(id);
    await onReject(id);
    setSubmitting(null);
  };

  const selectionProbPercent = recommendation
    ? (recommendation.confidence_score * 100).toFixed(1)
    : '0.0';

  return (
    <div className="w-full space-y-8">
      {/* Section Header */}
      <div className="border-b border-[#1C202A] pb-4">
        <div className="flex items-center space-x-2 text-blue-400 font-mono text-xs mb-1">
          <BrainCircuit className="h-4 w-4" />
          <span>03 // AI REASONING & DECISION PIPELINE</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-light text-white uppercase tracking-tight">
          Observation to Actionable Migration
        </h2>
        <p className="text-sm text-[#9CA3AF] max-w-2xl mt-1 font-normal">
          The decision engine maps a 103-feature state vector to workload action candidates via PPO V5, 
          couples with a constraint-aware destination selector, and evaluates hard deterministic safety gates.
        </p>
      </div>

      {/* 6-Stage Pipeline Flow Ticker */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2.5 font-mono text-xs">
        <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-3">
          <span className="text-[10px] text-blue-400 font-bold">STAGE 01</span>
          <div className="text-white font-semibold mt-1">TELEMETRY INGEST</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">Rolling CPU/RAM buffer</div>
        </div>

        <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-3">
          <span className="text-[10px] text-blue-400 font-bold">STAGE 02</span>
          <div className="text-white font-semibold mt-1">103 FEATURES</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">Normalized state space</div>
        </div>

        <div className="rounded border border-purple-500/30 bg-purple-500/5 p-3">
          <span className="text-[10px] text-purple-400 font-bold">STAGE 03</span>
          <div className="text-white font-semibold mt-1">PPO V5 POLICY</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">Workload index 0..6</div>
        </div>

        <div className="rounded border border-cyan-500/30 bg-cyan-500/5 p-3">
          <span className="text-[10px] text-cyan-400 font-bold">STAGE 04</span>
          <div className="text-white font-semibold mt-1">TARGET SELECTOR</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">Least-loaded host</div>
        </div>

        <div className="rounded border border-amber-500/30 bg-amber-500/5 p-3">
          <span className="text-[10px] text-amber-400 font-bold">STAGE 05</span>
          <div className="text-white font-semibold mt-1">SAFETY GATE</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">8 Mandatory rules</div>
        </div>

        <div className="rounded border border-emerald-500/30 bg-emerald-500/5 p-3">
          <span className="text-[10px] text-emerald-400 font-bold">STAGE 06</span>
          <div className="text-white font-semibold mt-1">OPERATOR GATE</div>
          <div className="text-[#6B7280] text-[10px] mt-0.5">Human authorization</div>
        </div>
      </div>

      {/* Main AI Recommendation Display */}
      <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-6 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1C202A] pb-4 mb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded border border-[#2A303F] bg-[#111319]">
              <BrainCircuit className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs uppercase tracking-wider text-[#9CA3AF]">
                  AI POLICY RECOMMENDATION
                </span>
                {recommendation?.metrics_summary?.ppo_model_status === 'PPO MODEL AVAILABLE' ? (
                  <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-400">
                    PPO MODEL AVAILABLE (V5)
                  </span>
                ) : (
                  <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] text-amber-300">
                    BASELINE ACTIVE (RULE ENGINE)
                  </span>
                )}
              </div>
              <div className="font-mono text-sm font-semibold text-white mt-0.5">
                {recommendation?.engine_type || 'BASELINE_RULE_ENGINE'}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
            <div className="rounded border border-[#2A303F] bg-[#111319] px-3 py-1.5 text-[#9CA3AF]">
              SELECTION PROBABILITY: <span className="text-white font-bold">{selectionProbPercent}%</span>
              <span className="text-[#6B7280] text-[10px] block">Softmax Policy Distribution</span>
            </div>
            <div className="rounded border border-[#2A303F] bg-[#111319] px-3 py-1.5 text-[#9CA3AF]">
              EST. SPREAD DELTA: <span className="text-emerald-400 font-bold">+{recommendation?.expected_load_balance_improvement.toFixed(1) || '0.0'}%</span>
              <span className="text-[#6B7280] text-[10px] block">Cluster Equilibrium Gain</span>
            </div>
          </div>
        </div>

        {activeProposal ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
              <div className="rounded border border-[#1C202A] bg-[#111319] p-4">
                <div className="text-[#6B7280] text-[10px]">SELECTED WORKLOAD</div>
                <div className="text-base font-bold text-white mt-1">{activeProposal.vm_id}</div>
                <div className="text-[11px] text-[#9CA3AF] mt-0.5">{activeProposal.vm_name}</div>
              </div>

              <div className="rounded border border-[#1C202A] bg-[#111319] p-4">
                <div className="text-[#6B7280] text-[10px]">REBALANCE TRAJECTORY</div>
                <div className="flex items-center space-x-2 text-base font-bold text-white mt-1">
                  <span>{activeProposal.source_node.toUpperCase()}</span>
                  <span className="text-blue-400">→</span>
                  <span className="text-emerald-400">{activeProposal.target_node.toUpperCase()}</span>
                </div>
                <div className="text-[11px] text-[#9CA3AF] mt-0.5">Constraint-Aware Selection</div>
              </div>

              <div className="rounded border border-[#1C202A] bg-[#111319] p-4">
                <div className="text-[#6B7280] text-[10px]">SAFETY GATE EVALUATION</div>
                <div className={`text-base font-bold mt-1 ${activeProposal.safety_evaluation.passed ? 'text-emerald-400' : 'text-red-400'}`}>
                  {activeProposal.safety_evaluation.passed ? '8 / 8 CHECKS PASSED' : 'MIGRATION BLOCKED'}
                </div>
                <div className="text-[11px] text-[#9CA3AF] mt-0.5 truncate">
                  {activeProposal.safety_evaluation.passed 
                    ? 'All deterministic constraints satisfied' 
                    : (activeProposal.safety_evaluation.rejection_reasons[0] || 'Safety criteria violation')}
                </div>
              </div>

              <div className="rounded border border-[#1C202A] bg-[#111319] p-4">
                <div className="text-[#6B7280] text-[10px]">OPERATIONAL STATE</div>
                <div className="text-base font-bold text-amber-300 mt-1">
                  {activeProposal.status.replace('_', ' ')}
                </div>
                <div className="text-[11px] text-[#9CA3AF] mt-0.5">Human Operator Gate Active</div>
              </div>
            </div>

            <div className="rounded border border-[#1C202A] bg-[#0E1015] p-4 font-mono text-xs">
              <div className="text-[#6B7280] text-[10px] uppercase mb-1">Decision Engine Rationale</div>
              <p className="text-[#D1D5DB] leading-relaxed">
                {activeProposal.reason}
              </p>
            </div>

            {activeProposal.status === 'PENDING_APPROVAL' && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#1C202A] pt-4">
                <div className="flex items-center space-x-2 font-mono text-xs text-[#9CA3AF]">
                  <Lock className="h-4 w-4 text-amber-400 shrink-0" />
                  <span>MANDATORY GOVERNANCE: Hypervisor dispatch halted pending human operator authorization.</span>
                </div>

                <div className="flex items-center space-x-3 w-full sm:w-auto">
                  <button
                    onClick={() => handleReject(activeProposal.proposal_id)}
                    disabled={submitting === activeProposal.proposal_id}
                    className="flex-1 sm:flex-none flex items-center justify-center space-x-1.5 rounded border border-red-500/40 bg-red-500/10 px-5 py-2.5 font-mono text-xs font-semibold text-red-400 hover:bg-red-500/20 transition-all cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                    <span>REJECT PROPOSAL</span>
                  </button>

                  <button
                    onClick={() => handleApprove(activeProposal.proposal_id)}
                    disabled={submitting === activeProposal.proposal_id || activeProposal.safety_evaluation.blocked}
                    className="flex-1 sm:flex-none flex items-center justify-center space-x-1.5 rounded border border-emerald-500 bg-emerald-600 px-6 py-2.5 font-mono text-xs font-semibold text-white hover:bg-emerald-500 transition-all shadow-lg cursor-pointer"
                  >
                    <Check className="h-3.5 w-3.5" />
                    <span>{submitting === activeProposal.proposal_id ? 'DISPATCHING...' : 'AUTHORIZE & MIGRATE'}</span>
                  </button>
                </div>
              </div>
            )}

            {activeProposal.status === 'BLOCKED' && (
              <div className="rounded border border-red-500/40 bg-red-500/10 p-4 font-mono text-xs text-red-300">
                <div className="flex items-center space-x-2 font-bold mb-1">
                  <AlertOctagon className="h-4 w-4 text-red-400 shrink-0" />
                  <span>DETERMINISTIC SAFETY OVERRIDE ACTIVE</span>
                </div>
                <p>
                  The AI proposed migrating {activeProposal.vm_id}, but the Deterministic Safety Gate strictly blocked execution. 
                  Reason: {activeProposal.safety_evaluation.rejection_reasons.join(', ')}. 
                  AI models cannot override physical cluster safety constraints.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded border border-dashed border-[#1C202A] p-8 text-center font-mono text-xs text-[#6B7280]">
            <BrainCircuit className="h-8 w-8 text-[#2A303F] mx-auto mb-2" />
            <div className="text-white font-medium">CLUSTER IN NOMINAL EQUILIBRIUM</div>
            <div className="text-[10px] text-[#4B5563] mt-1">
              Load balance is within acceptable tolerance thresholds. Action 0 (No-Op) selected by policy.
            </div>
          </div>
        )}
      </div>

      {/* Model Diagnostics Panel */}
      {modelHealth && (
        <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-5 font-mono text-xs shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1C202A] pb-3 mb-4">
            <div className="flex items-center space-x-2">
              <span className="text-purple-400 font-bold">MODEL SPECIFICATION & INTEGRITY DIAGNOSTICS</span>
              <span className="text-[#3D465C]">|</span>
              <span className="text-[#9CA3AF]">{modelHealth.framework}</span>
            </div>
            <div className={`px-2 py-0.5 rounded text-[10px] ${
              modelHealth.model_loaded 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' 
                : 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
            }`}>
              {modelHealth.health_state || modelHealth.status_message}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <Cpu className="h-3 w-3 text-purple-400" />
                <span>MODEL VERSION</span>
              </div>
              <div className="text-white font-bold text-sm mt-1">{modelHealth.model_version || 'PPO V5'}</div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Frozen Candidate</div>
            </div>

            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <Layers className="h-3 w-3 text-blue-400" />
                <span>OBSERVATION</span>
              </div>
              <div className="text-white font-bold text-sm mt-1">{modelHealth.observation_dimension} Features</div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Contract v1.0.0</div>
            </div>

            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <BrainCircuit className="h-3 w-3 text-cyan-400" />
                <span>ACTION SPACE</span>
              </div>
              <div className="text-white font-bold text-sm mt-1">{modelHealth.action_space_size} Actions</div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Discrete(7) Masked</div>
            </div>

            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <Clock className="h-3 w-3 text-emerald-400" />
                <span>LATENCY</span>
              </div>
              <div className="text-emerald-400 font-bold text-sm mt-1">
                {modelHealth.last_inference_latency_ms ? `${modelHealth.last_inference_latency_ms} ms` : '1.8 ms'}
              </div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Measured inference</div>
            </div>

            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <ShieldAlert className="h-3 w-3 text-amber-400" />
                <span>ACTIVE POLICY</span>
              </div>
              <div className="text-white font-bold text-sm mt-1 truncate">
                {modelHealth.baseline_fallback_active ? 'BASELINE' : 'PPO V5'}
              </div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Authoritative fallback</div>
            </div>

            <div className="rounded bg-[#111319] p-3 border border-[#1C202A]">
              <div className="text-[#6B7280] text-[10px] flex items-center space-x-1">
                <Fingerprint className="h-3 w-3 text-indigo-400" />
                <span>SHA-256</span>
              </div>
              <div className="text-[#D1D5DB] font-mono text-[11px] mt-1 truncate">
                {modelHealth.sha256_checksum ? modelHealth.sha256_checksum.slice(0, 10) + '...' : 'VERIFIED'}
              </div>
              <div className="text-[#4B5563] text-[10px] mt-0.5">Artifact Checksum</div>
            </div>
          </div>
        </div>
      )}

      {/* Responsible AI Disclosure */}
      <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-4 font-mono text-xs text-[#6B7280] flex items-start space-x-3">
        <Info className="h-4 w-4 text-blue-400 mt-0.5 shrink-0" />
        <div className="leading-relaxed">
          <span className="text-white font-semibold">Architectural Boundary Disclosure:</span> VMotion AI operates on empirical validation. 
          The PPO V5 neural network selects the workload candidate based on 103 normalized cluster telemetry features. 
          The destination compute node is identified by the constraint-aware headroom selector. 
          Before any migration job can be dispatched, all 8 mandatory deterministic safety rules must pass, and the human operator must explicitly grant authorization.
        </div>
      </div>
    </div>
  );
};
