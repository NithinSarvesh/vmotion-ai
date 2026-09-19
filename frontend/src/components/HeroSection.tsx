import React from 'react';
import { ArrowRight, Cpu, Activity, AlertTriangle } from 'lucide-react';
import type { ClusterState, Recommendation, PendingProposal, AggregatedClusterTelemetry } from '../types';

interface HeroSectionProps {
  cluster: ClusterState | null;
  telemetry?: AggregatedClusterTelemetry | null;
  recommendation?: Recommendation | null;
  proposals: PendingProposal[];
  onNavigateTab: (tab: string) => void;
  onTriggerAi?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  cluster,
  telemetry,
  proposals,
  onNavigateTab
}) => {
  const nodes = cluster ? Object.values(cluster.nodes) : [];
  const vms = cluster ? Object.values(cluster.vms) : [];
  const pendingProposal = proposals.find(p => p.status === 'PENDING_APPROVAL');

  return (
    <section className="relative overflow-hidden border-b border-[#1C202A] technical-grid py-14 lg:py-20">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[700px] -translate-x-1/2 rounded-full bg-blue-500/5 blur-3xl" />
      <div className="pointer-events-none absolute top-1/2 right-10 h-64 w-64 rounded-full bg-emerald-500/5 blur-3xl" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          <div className="lg:col-span-7 flex flex-col space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded border border-[#2A303F] bg-[#111319] px-2.5 py-0.5 font-mono text-[11px] text-[#9CA3AF]">
                CONTROL PLANE FOUNDATION v1.0
              </span>
              <span className="inline-flex items-center rounded border border-purple-500/30 bg-purple-500/10 px-2.5 py-0.5 font-mono text-[11px] text-purple-400">
                PPO V5 (103 FEATURES)
              </span>
              <span className="inline-flex items-center rounded border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 font-mono text-[11px] text-emerald-400">
                8-RULE SAFETY GATE
              </span>
            </div>

            <div>
              <div className="font-mono text-xs text-blue-400 tracking-widest uppercase mb-1">
                VMOTION AI // INFRASTRUCTURE SUPERVISOR
              </div>
              <h1 className="text-4xl sm:text-6xl lg:text-7xl font-light tracking-tight text-white uppercase leading-[1.05]">
                Intelligent <br />
                <span className="font-semibold text-transparent bg-clip-text bg-gradient-to-r from-white via-[#E5E7EB] to-[#9CA3AF]">
                  Infrastructure.
                </span>
              </h1>
            </div>

            <p className="text-base text-[#9CA3AF] max-w-xl font-normal leading-relaxed">
              Real telemetry meets reinforcement learning and deterministic safety gates. 
              Virtual machine migration orchestrator engineered for cluster rebalancing with verified destination placement and workload health validation.
            </p>

            {/* Signature 5-Phase Pipeline */}
            <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-3 max-w-xl">
              <div className="text-[10px] font-mono text-[#6B7280] uppercase tracking-wider mb-2">
                Operational Rebalancing Pipeline:
              </div>
              <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                <span className="flex items-center space-x-1 text-white">
                  <span className="text-blue-400 font-bold">01</span>
                  <span>OBSERVE</span>
                </span>
                <span className="text-[#3D465C]">→</span>
                <span className="flex items-center space-x-1 text-white">
                  <span className="text-purple-400 font-bold">02</span>
                  <span>DECIDE</span>
                </span>
                <span className="text-[#3D465C]">→</span>
                <span className="flex items-center space-x-1 text-white">
                  <span className="text-amber-400 font-bold">03</span>
                  <span>GATE</span>
                </span>
                <span className="text-[#3D465C]">→</span>
                <span className="flex items-center space-x-1 text-white">
                  <span className="text-cyan-400 font-bold">04</span>
                  <span>MIGRATE</span>
                </span>
                <span className="text-[#3D465C]">→</span>
                <span className="flex items-center space-x-1 text-white">
                  <span className="text-emerald-400 font-bold">05</span>
                  <span>VERIFY</span>
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-1">
              <button
                onClick={() => onNavigateTab('topology')}
                className="flex items-center space-x-2 rounded border border-[#3D465C] bg-[#161922] px-5 py-2.5 font-mono text-xs font-medium text-white hover:border-blue-500 hover:bg-[#1F2430] transition-all shadow-lg cursor-pointer"
              >
                <span>OPEN TOPOLOGY FABRIC</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>

              <button
                onClick={() => onNavigateTab('ai-engine')}
                className="flex items-center space-x-2 rounded border border-[#2A303F] bg-[#111319] px-5 py-2.5 font-mono text-xs font-medium text-[#9CA3AF] hover:text-white hover:border-[#3D465C] transition-all cursor-pointer"
              >
                <Cpu className="h-3.5 w-3.5 text-blue-400" />
                <span>INSPECT AI SAFETY GATE</span>
              </button>
            </div>
          </div>

          <div className="lg:col-span-5">
            <div className="rounded border border-[#1C202A] bg-[#0A0C10]/95 p-5 shadow-2xl backdrop-blur-sm">
              <div className="flex items-center justify-between border-b border-[#1C202A] pb-3 mb-4 font-mono text-xs">
                <div className="flex items-center space-x-2">
                  <Activity className="h-4 w-4 text-emerald-400 animate-pulse" />
                  <span className="text-white font-medium">CLUSTER TOPOLOGY STATE</span>
                </div>
                <span className="text-[#6B7280]">
                  {nodes.length} NODES / {vms.length} VMS
                </span>
              </div>

              {/* Cluster Macro Health Gauges */}
              <div className="grid grid-cols-3 gap-2 mb-4 font-mono text-xs">
                <div className="rounded border border-[#1C202A] bg-[#111319] p-2 text-center">
                  <div className="text-[10px] text-[#6B7280]">FAIRNESS</div>
                  <div className="text-sm font-bold text-emerald-400">
                    {telemetry?.jains_fairness_cpu ? telemetry.jains_fairness_cpu.toFixed(3) : '0.960'}
                  </div>
                </div>
                <div className="rounded border border-[#1C202A] bg-[#111319] p-2 text-center">
                  <div className="text-[10px] text-[#6B7280]">CPU SPREAD</div>
                  <div className="text-sm font-bold text-white">
                    {telemetry?.cluster_cpu_imbalance_std ? `${telemetry.cluster_cpu_imbalance_std.toFixed(1)}%` : '0.0%'}
                  </div>
                </div>
                <div className="rounded border border-[#1C202A] bg-[#111319] p-2 text-center">
                  <div className="text-[10px] text-[#6B7280]">RAM LOAD</div>
                  <div className="text-sm font-bold text-indigo-400">
                    {telemetry ? `${((telemetry.total_ram_used_gb / Math.max(1, telemetry.total_ram_total_gb)) * 100).toFixed(0)}%` : '54%'}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                {nodes.map((node) => {
                  const hostedVMs = vms.filter(v => v.node_id === node.id);
                  const isHot = node.cpu_percent > 75.0;

                  return (
                    <div 
                      key={node.id}
                      className="rounded border border-[#1C202A] bg-[#111319] p-3 hover:border-[#2A303F] transition-all"
                    >
                      <div className="flex items-center justify-between font-mono text-xs mb-2">
                        <div className="flex items-center space-x-2">
                          <span className={`h-2 w-2 rounded-full ${node.status === 'online' ? (isHot ? 'bg-amber-400' : 'bg-emerald-400') : 'bg-red-500'}`} />
                          <span className="font-semibold text-white">{node.id.toUpperCase()}</span>
                          <span className="text-[10px] text-[#6B7280]">({node.name})</span>
                        </div>
                        <span className={`text-xs font-medium ${isHot ? 'text-amber-400 font-bold' : 'text-[#9CA3AF]'}`}>
                          CPU {node.cpu_percent.toFixed(1)}%
                        </span>
                      </div>

                      <div className="w-full bg-[#08090C] rounded-full h-1.5 overflow-hidden mb-2">
                        <div 
                          className={`h-full transition-all duration-500 ${isHot ? 'bg-amber-400' : 'bg-blue-500'}`} 
                          style={{ width: `${Math.min(100, node.cpu_percent)}%` }}
                        />
                      </div>

                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {hostedVMs.map((vm) => (
                          <span 
                            key={vm.vmid}
                            className={`rounded px-1.5 py-0.5 font-mono text-[10px] border ${
                              vm.status === 'migrating'
                                ? 'border-amber-500/50 bg-amber-500/20 text-amber-300 animate-pulse'
                                : 'border-[#2A303F] bg-[#08090C] text-[#9CA3AF]'
                            }`}
                          >
                            {vm.vmid} ({vm.cpu_percent.toFixed(0)}% CPU)
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              {pendingProposal && (
                <div className="mt-4 rounded border border-amber-500/30 bg-amber-500/5 p-3">
                  <div className="flex items-center justify-between font-mono text-xs text-amber-300 mb-1">
                    <span className="flex items-center space-x-1">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                      <span>PENDING AI PROPOSAL</span>
                    </span>
                    <span className="text-[10px] bg-amber-500/20 px-1.5 py-0.5 rounded">
                      APPROVAL NEEDED
                    </span>
                  </div>
                  <p className="text-xs text-[#9CA3AF] line-clamp-1 font-mono">
                    Migrate {pendingProposal.vm_id} ({pendingProposal.source_node} → {pendingProposal.target_node})
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
