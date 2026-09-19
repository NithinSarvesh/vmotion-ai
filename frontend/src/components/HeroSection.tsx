import React from 'react';
import { ArrowRight, Cpu, Activity, Database, Layers } from 'lucide-react';
import type { ClusterState, Recommendation, PendingProposal, AggregatedClusterTelemetry } from '../types';
import { HeroCluster3D } from './HeroCluster3D';

interface HeroSectionProps {
  cluster: ClusterState | null;
  telemetry?: AggregatedClusterTelemetry | null;
  recommendation?: Recommendation | null;
  proposals: PendingProposal[];
  onNavigateSection: (sectionId: string) => void;
  onTriggerAi?: () => void;
  onSelectNode?: (nodeId: string) => void;
  onSelectVm?: (vmId: string) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  cluster,
  telemetry,
  recommendation,
  proposals,
  onNavigateSection,
  onSelectNode,
  onSelectVm
}) => {
  const nodes = cluster ? Object.values(cluster.nodes) : [];
  const vms = cluster ? Object.values(cluster.vms) : [];
  const pendingProposal = proposals.find(p => p.status === 'PENDING_APPROVAL');

  const avgCpu = telemetry ? telemetry.avg_cluster_cpu_percent : 0;
  const jainsFairness = telemetry ? telemetry.jains_fairness_cpu.toFixed(3) : '1.000';
  const totalRamGb = telemetry ? telemetry.total_ram_total_gb : 0;
  const usedRamGb = telemetry ? telemetry.total_ram_used_gb : 0;

  return (
    <section className="relative w-full pt-10 pb-16 lg:py-16">
      {/* Editorial Headline & Top Narrative Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center mb-12">
        
        {/* Left Column: Editorial Typography */}
        <div className="lg:col-span-7 flex flex-col space-y-6">
          
          {/* Architecture Badges */}
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
            <span className="inline-flex items-center rounded-md border border-[#CBD5E1] bg-white px-2.5 py-1 text-[#334155] shadow-2xs font-semibold">
              CONTROL PLANE FOUNDATION v1.0
            </span>
            <span className="inline-flex items-center rounded-md border border-purple-200 bg-purple-50 px-2.5 py-1 text-purple-800 font-semibold">
              PPO V5 (103 FEATURES)
            </span>
            <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-emerald-800 font-semibold">
              8-RULE SAFETY GATE
            </span>
            <span className="inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-amber-800 font-semibold">
              HUMAN-IN-THE-LOOP
            </span>
          </div>

          {/* Large Title */}
          <div>
            <div className="font-mono text-xs font-bold text-blue-600 tracking-widest uppercase mb-2">
              VMOTION AI // INFRASTRUCTURE SUPERVISOR
            </div>
            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-light tracking-tight text-[#0F172A] leading-[1.05]">
              INTELLIGENT <br />
              <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-[#0F172A] via-[#1E293B] to-[#475569]">
                INFRASTRUCTURE.
              </span>
            </h1>
          </div>

          {/* Supporting Copy */}
          <p className="text-base sm:text-lg text-[#475569] max-w-xl font-normal leading-relaxed">
            AI-assisted virtual machine migration with deterministic safety controls, 
            human approval, and verified post-migration state.
          </p>

          {/* Operational Pipeline Ribbon */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs max-w-xl">
            <div className="text-[10px] font-mono font-bold text-[#94A3B8] uppercase tracking-wider mb-2.5">
              Deterministic Rebalance Lifecycle:
            </div>
            <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
              <span className="flex items-center space-x-1.5 text-[#0F172A]">
                <span className="font-bold text-blue-600">01</span>
                <span>OBSERVE</span>
              </span>
              <span className="text-[#CBD5E1]">→</span>
              <span className="flex items-center space-x-1.5 text-[#0F172A]">
                <span className="font-bold text-purple-600">02</span>
                <span>DECIDE</span>
              </span>
              <span className="text-[#CBD5E1]">→</span>
              <span className="flex items-center space-x-1.5 text-[#0F172A]">
                <span className="font-bold text-amber-600">03</span>
                <span>GATE</span>
              </span>
              <span className="text-[#CBD5E1]">→</span>
              <span className="flex items-center space-x-1.5 text-[#0F172A]">
                <span className="font-bold text-cyan-600">04</span>
                <span>MIGRATE</span>
              </span>
              <span className="text-[#CBD5E1]">→</span>
              <span className="flex items-center space-x-1.5 text-[#0F172A]">
                <span className="font-bold text-emerald-600">05</span>
                <span>VERIFY</span>
              </span>
            </div>
          </div>

          {/* Call to Actions */}
          <div className="flex flex-wrap items-center gap-3 pt-2 font-mono text-xs">
            <button
              onClick={() => onNavigateSection('topology')}
              className="flex items-center space-x-2 rounded-lg bg-[#0F172A] px-5 py-3 font-semibold text-white hover:bg-[#1E293B] transition-all shadow-sm cursor-pointer"
            >
              <span>EXPLORE COMPUTE FABRIC</span>
              <ArrowRight className="h-4 w-4" />
            </button>

            <button
              onClick={() => onNavigateSection('ai-engine')}
              className="flex items-center space-x-2 rounded-lg border border-[#CBD5E1] bg-white px-5 py-3 font-semibold text-[#0F172A] hover:bg-[#F8FAFC] hover:border-[#94A3B8] transition-all shadow-xs cursor-pointer"
            >
              <span>INSPECT AI PIPELINE</span>
            </button>
          </div>
        </div>

        {/* Right Column: 3D Interactive Spatial Cluster */}
        <div className="lg:col-span-5 w-full">
          <HeroCluster3D
            cluster={cluster}
            recommendation={recommendation}
            onSelectNode={onSelectNode}
            onSelectVm={onSelectVm}
          />
        </div>
      </div>

      {/* Cluster Telemetry Metrics Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#64748B]">
            <span className="text-[10px] uppercase tracking-wider font-semibold">AVERAGE CPU UTILIZATION</span>
            <Cpu className="h-4 w-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-[#0F172A] mt-2">{avgCpu}%</div>
          <div className="text-[11px] text-[#64748B] mt-1">Across {nodes.length} compute hosts</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#64748B]">
            <span className="text-[10px] uppercase tracking-wider font-semibold">JAIN'S FAIRNESS INDEX</span>
            <Activity className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-[#0F172A] mt-2">{jainsFairness}</div>
          <div className="text-[11px] text-[#64748B] mt-1">1.000 = perfectly balanced load</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#64748B]">
            <span className="text-[10px] uppercase tracking-wider font-semibold">MEMORY ALLOCATION</span>
            <Database className="h-4 w-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-[#0F172A] mt-2">{usedRamGb.toFixed(1)} / {totalRamGb.toFixed(0)} GB</div>
          <div className="text-[11px] text-[#64748B] mt-1">Host RAM footprint</div>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#64748B]">
            <span className="text-[10px] uppercase tracking-wider font-semibold">ACTIVE WORKLOADS</span>
            <Layers className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-[#0F172A] mt-2">{vms.length} VMs</div>
          <div className="text-[11px] text-[#64748B] mt-1">
            {pendingProposal ? (
              <span className="text-amber-600 font-semibold">1 migration proposal pending</span>
            ) : (
              <span>Cluster state in equilibrium</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
