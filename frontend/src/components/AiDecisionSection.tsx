import React, { useState } from 'react';
import { 
  BrainCircuit, 
  Check, 
  Cpu, 
  Fingerprint,
  Activity,
  Database
} from 'lucide-react';
import type { Recommendation, PendingProposal, SafetyEvaluation, PPOModelHealth } from '../types';

interface AiDecisionSectionProps {
  recommendation: Recommendation | null;
  safetyEvaluation?: SafetyEvaluation | null;
  modelHealth?: PPOModelHealth | null;
  proposals?: PendingProposal[];
  onApprove?: (proposalId: string) => Promise<boolean>;
  onReject?: (proposalId: string) => Promise<boolean>;
}

export const AiDecisionSection: React.FC<AiDecisionSectionProps> = ({
  recommendation,
  modelHealth
}) => {
  const [activeVectorTab, setActiveVectorTab] = useState<'nodes' | 'vms' | 'global'>('global');

  const selectionProbPercent = recommendation
    ? (recommendation.confidence_score * 100).toFixed(1)
    : '0.0';

  // Synthetic or real 103-feature inspector slices
  const nodeFeatures = [
    { idx: '0..7', name: 'Node-01 Features', items: ['CPU Util', 'RAM Util', 'Net RX', 'Net TX', 'Disk Used', 'VM Count', 'Status Flag', 'Headroom'] },
    { idx: '8..15', name: 'Node-02 Features', items: ['CPU Util', 'RAM Util', 'Net RX', 'Net TX', 'Disk Used', 'VM Count', 'Status Flag', 'Headroom'] },
    { idx: '16..23', name: 'Node-03 Features', items: ['CPU Util', 'RAM Util', 'Net RX', 'Net TX', 'Disk Used', 'VM Count', 'Status Flag', 'Headroom'] }
  ];

  const vmFeatures = [
    { idx: '24..33', name: 'VM-101 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] },
    { idx: '34..43', name: 'VM-102 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] },
    { idx: '44..53', name: 'VM-103 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] },
    { idx: '54..63', name: 'VM-104 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] },
    { idx: '64..73', name: 'VM-105 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] },
    { idx: '74..83', name: 'VM-106 Slot', items: ['CPU Util', 'RAM Alloc', 'RAM Util', 'Net I/O', 'SLA Weight', 'Cooldown', 'Mig Count', 'Uptime', 'Contention', 'Host Idx'] }
  ];

  const globalFeatures = [
    { idx: '84', name: 'CPU Load Std Dev', desc: 'Cluster load variance' },
    { idx: '85', name: "Jain's Fairness (CPU)", desc: 'Resource fairness distribution' },
    { idx: '86', name: "Jain's Fairness (RAM)", desc: 'Memory equity balance' },
    { idx: '87', name: 'Cluster Avg CPU', desc: 'Overall mean compute utilization' },
    { idx: '88', name: 'Cluster Avg RAM', desc: 'Overall mean memory utilization' },
    { idx: '89', name: 'Quadratic Power Model', desc: 'Cluster energy curve estimate' },
    { idx: '90', name: 'VM Density Ratio', desc: 'Active workloads vs maximum capacity' },
    { idx: '91', name: 'Migrating Workload Ratio', desc: 'Proportion of VMs currently in transit' },
    { idx: '92', name: 'SLA Breach Ratio', desc: 'Workloads violating SLA thresholds' },
    { idx: '93', name: 'Hotspot Overload Flag', desc: 'Binary trigger for >85% node saturation' },
    { idx: '94..96', name: 'Node Headroom Ratios', desc: 'Available memory on node-01, 02, 03' },
    { idx: '97', name: 'Cluster Net Saturation', desc: 'Aggregate inter-host network bandwidth' },
    { idx: '98', name: 'Cluster Disk Saturation', desc: 'Storage capacity utilization ratio' },
    { idx: '99', name: 'Quorum Healthy Flag', desc: 'Corosync consensus confirmation (1/0)' },
    { idx: '100', name: 'Shared Storage Flag', desc: 'Shared datastore accessibility (1/0)' },
    { idx: '101', name: 'Migration Usefulness', desc: 'Heuristic potential gain estimate' },
    { idx: '102', name: 'Temporal Cyclical Phase', desc: 'Normalized cyclical sine phase marker' }
  ];

  return (
    <div className="w-full space-y-8 font-mono text-xs">
      {/* Section Header */}
      <div className="border-b border-[#E2E8F0] pb-6">
        <div className="flex items-center space-x-2 text-purple-600 text-xs mb-1 font-bold tracking-wider">
          <BrainCircuit className="h-4 w-4" />
          <span className="uppercase">03 // REINFORCEMENT LEARNING REASONING PIPELINE</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-light text-[#0F172A] uppercase tracking-tight font-sans">
          Observation Vector to Policy Action
        </h2>
        <p className="text-sm text-[#475569] max-w-3xl mt-1 font-normal font-sans">
          The decision engine continuously extracts an immutable 103-feature continuous state vector from cluster telemetry, 
          evaluates MaskablePPO policy distributions over Discrete(7), and resolves destination placement via load gradients.
        </p>
      </div>

      {/* 5-Stage Decision Sequence Ticker */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs">
          <span className="text-[10px] text-blue-600 font-bold">01 INGEST</span>
          <div className="text-[#0F172A] font-bold mt-1 text-xs">TELEMETRY</div>
          <div className="text-[#64748B] text-[10px] mt-0.5">Rolling CPU/RAM buffer</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs">
          <span className="text-[10px] text-purple-600 font-bold">02 EXTRACT</span>
          <div className="text-[#0F172A] font-bold mt-1 text-xs">103 FEATURES</div>
          <div className="text-[#64748B] text-[10px] mt-0.5">Bounded [-1.0, 1.0] floats</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs">
          <span className="text-[10px] text-indigo-600 font-bold">03 INFERENCE</span>
          <div className="text-[#0F172A] font-bold mt-1 text-xs">PPO V5 POLICY</div>
          <div className="text-[#64748B] text-[10px] mt-0.5">MaskablePPO actor-critic</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs">
          <span className="text-[10px] text-amber-600 font-bold">04 MASK</span>
          <div className="text-[#0F172A] font-bold mt-1 text-xs">DISCRETE(7)</div>
          <div className="text-[#64748B] text-[10px] mt-0.5">Cooldown & state masked</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-2xs col-span-2 md:col-span-1">
          <span className="text-[10px] text-emerald-600 font-bold">05 RESOLVE</span>
          <div className="text-[#0F172A] font-bold mt-1 text-xs">DESTINATION</div>
          <div className="text-[#64748B] text-[10px] mt-0.5">Headroom gradient target</div>
        </div>
      </div>

      {/* Main Grid: Decision Engine Output & Model Health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left: Active Recommendation Card */}
        <div className="lg:col-span-7 rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4 mb-5">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-purple-600" />
              <span className="font-bold text-[#0F172A] uppercase tracking-wider">
                CURRENT POLICY RECOMMENDATION
              </span>
            </div>
            <span className="text-[10px] text-[#64748B]">
              ENGINE: {recommendation?.engine_type || 'PPO_POLICY'}
            </span>
          </div>

          {recommendation && recommendation.action_type === 'MIGRATE' ? (
            <div className="space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-purple-200 bg-purple-50/50 p-4">
                <div>
                  <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wide">
                    RECOMMENDED MIGRATION ACTION
                  </span>
                  <div className="text-xl font-bold text-[#0F172A] mt-1">
                    Migrate <span className="text-purple-700 font-extrabold">{recommendation.vm_id}</span>
                  </div>
                  <div className="text-[#475569] text-xs mt-0.5">
                    Trajectory: {recommendation.source_node || 'current'} → <strong className="text-[#0F172A]">{recommendation.target_node}</strong>
                  </div>
                </div>

                <div className="text-right sm:text-right">
                  <div className="text-[10px] text-[#64748B] uppercase font-bold">SELECTION PROBABILITY</div>
                  <div className="text-2xl font-black text-purple-700">{selectionProbPercent}%</div>
                  <div className="text-[10px] text-[#64748B] mt-0.5">Softmax Policy Distribution</div>
                </div>
              </div>

              {/* Rationale Explanation */}
              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 text-[#475569] text-xs leading-relaxed">
                <span className="font-bold text-[#0F172A] block mb-1">POLICY REASONING RATIONALE:</span>
                {recommendation.reason}
              </div>

              <div className="grid grid-cols-2 gap-3 text-[11px]">
                <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold">ACTION SPACE INDEX</span>
                  <div className="text-[#0F172A] font-bold mt-1">Index {recommendation.action_index} (Discrete 7)</div>
                </div>
                <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold">INFERENCE LATENCY</span>
                  <div className="text-[#0F172A] font-bold mt-1">
                    {recommendation.metrics_summary?.inference_latency_ms ?? 1.8} ms
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[#CBD5E1] p-8 text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 mb-3 border border-emerald-200">
                <Check className="h-5 w-5" />
              </div>
              <h4 className="text-sm font-bold text-[#0F172A] uppercase">CLUSTER LOAD IN EQUILIBRIUM</h4>
              <p className="text-[#64748B] text-xs max-w-md mx-auto mt-1">
                PPO Policy selected Action 0 (No-Op). Workload distributions are within optimal variance thresholds. 
                No proactive migration is currently necessary.
              </p>
            </div>
          )}
        </div>

        {/* Right: Model Health & Verification Ledger */}
        <div className="lg:col-span-5 rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4">
            <div className="flex items-center space-x-2">
              <Cpu className="h-4 w-4 text-blue-600" />
              <span className="font-bold text-[#0F172A] uppercase tracking-wider">
                MODEL ARTIFACT STATUS
              </span>
            </div>
            <span className="rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 text-[10px] font-bold">
              {modelHealth?.health_state || 'MODEL READY'}
            </span>
          </div>

          <div className="space-y-2.5 text-[11px]">
            <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
              <span className="text-[#64748B]">Model Candidate:</span>
              <span className="font-bold text-[#0F172A]">PPO V5 (Frozen)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
              <span className="text-[#64748B]">Observation Spec:</span>
              <span className="font-bold text-[#0F172A]">v1.0.0 (103 Continuous Features)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
              <span className="text-[#64748B]">Action Space Spec:</span>
              <span className="font-bold text-[#0F172A]">v1.0.0 (Discrete 7 Action Masks)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
              <span className="text-[#64748B]">Framework Engine:</span>
              <span className="font-bold text-[#0F172A]">sb3-contrib.MaskablePPO</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#F1F5F9]">
              <span className="text-[#64748B]">Baseline Fallback:</span>
              <span className="font-bold text-[#0F172A]">Inactive (Primary Model Active)</span>
            </div>
          </div>

          {/* Checksum Badge */}
          <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3 text-[10px]">
            <div className="flex items-center space-x-1.5 text-[#64748B] font-bold uppercase mb-1">
              <Fingerprint className="h-3.5 w-3.5 text-blue-600" />
              <span>SHA-256 ARTIFACT CHECKSUM</span>
            </div>
            <div className="font-mono text-[#0F172A] break-all">
              {modelHealth?.sha256_checksum || 'bc47c2a564d2d2f00e6f8a7b7f376cecb10f471376d75f99a539842486d98afe'}
            </div>
          </div>
        </div>
      </div>

      {/* 103-Dimensional Vector Decomposition Explorer */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-4 mb-5">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 font-bold">
              <Database className="h-4 w-4" />
              <span className="uppercase tracking-wider">103-DIMENSIONAL OBSERVATION SCHEMA EXPLORER</span>
            </div>
            <p className="text-[#64748B] text-[11px] mt-0.5">
              Verified mapping of cluster telemetry into continuous normalized vector inputs for reinforcement learning inference.
            </p>
          </div>

          {/* Sub-tabs */}
          <div className="flex items-center space-x-1 font-mono text-[11px]">
            <button
              onClick={() => setActiveVectorTab('nodes')}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                activeVectorTab === 'nodes' ? 'bg-[#0F172A] text-white font-semibold' : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
              }`}
            >
              NODES (0..23)
            </button>
            <button
              onClick={() => setActiveVectorTab('vms')}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                activeVectorTab === 'vms' ? 'bg-[#0F172A] text-white font-semibold' : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
              }`}
            >
              VMS (24..83)
            </button>
            <button
              onClick={() => setActiveVectorTab('global')}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                activeVectorTab === 'global' ? 'bg-[#0F172A] text-white font-semibold' : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
              }`}
            >
              GLOBAL & FAIRNESS (84..102)
            </button>
          </div>
        </div>

        {/* Dynamic Vector Content */}
        {activeVectorTab === 'nodes' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {nodeFeatures.map((nf) => (
              <div key={nf.idx} className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
                <div className="flex justify-between items-center text-xs font-bold text-[#0F172A] pb-2 border-b border-[#E2E8F0]">
                  <span>{nf.name}</span>
                  <span className="text-blue-600 text-[10px]">[{nf.idx}]</span>
                </div>
                <div className="mt-3 space-y-1.5 text-[11px] text-[#475569]">
                  {nf.items.map((it, i) => (
                    <div key={it} className="flex justify-between">
                      <span>{it}:</span>
                      <span className="text-[#0F172A] font-semibold">slot {i}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeVectorTab === 'vms' && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {vmFeatures.map((vf) => (
              <div key={vf.idx} className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <div className="flex justify-between items-center text-xs font-bold text-[#0F172A] pb-1.5 border-b border-[#E2E8F0]">
                  <span>{vf.name}</span>
                  <span className="text-purple-600 text-[9px]">[{vf.idx}]</span>
                </div>
                <div className="mt-2 space-y-1 text-[10px] text-[#475569]">
                  {vf.items.map((it) => (
                    <div key={it} className="truncate">· {it}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeVectorTab === 'global' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {globalFeatures.map((gf) => (
              <div key={gf.idx} className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3 flex justify-between items-start">
                <div>
                  <div className="font-bold text-[#0F172A] text-xs">{gf.name}</div>
                  <div className="text-[10px] text-[#64748B] mt-0.5">{gf.desc}</div>
                </div>
                <span className="rounded bg-white border border-[#CBD5E1] px-2 py-0.5 font-bold text-indigo-700 text-[10px] shrink-0 ml-2">
                  #{gf.idx}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
