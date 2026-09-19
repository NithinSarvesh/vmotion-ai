import React, { useState } from 'react';
import { 
  Server, 
  Cpu, 
  HardDrive, 
  Zap, 
  Network,
  X,
  ArrowRight,
  Activity,
  Gauge
} from 'lucide-react';
import type { 
  ClusterState, 
  NodeTelemetry, 
  VMTelemetry, 
  MigrationTaskStatus, 
  AggregatedClusterTelemetry,
  Recommendation
} from '../types';

interface TopologyCanvasProps {
  cluster: ClusterState | null;
  telemetry?: AggregatedClusterTelemetry | null;
  activeTasks: MigrationTaskStatus[];
  recommendation?: Recommendation | null;
}

export const TopologyCanvas: React.FC<TopologyCanvasProps> = ({
  cluster,
  telemetry,
  activeTasks,
  recommendation
}) => {
  const [selectedVm, setSelectedVm] = useState<VMTelemetry | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeTelemetry | null>(null);
  const [filterSla, setFilterSla] = useState<string>('all');

  const nodes = cluster ? Object.values(cluster.nodes) : [];
  const vms = cluster ? Object.values(cluster.vms) : [];

  const activeTask = activeTasks.length > 0 ? activeTasks[0] : null;

  // Active migration or pending candidate migration vector
  const migrationVector = activeTask 
    ? {
        type: 'ACTIVE_MIGRATION',
        vm_id: activeTask.vm_id,
        source: activeTask.source_node,
        target: activeTask.target_node,
        progress: activeTask.progress_percent,
        state: activeTask.state
      }
    : (recommendation && recommendation.action_type === 'MIGRATE' && recommendation.vm_id && recommendation.target_node)
    ? {
        type: 'CANDIDATE_VECTOR',
        vm_id: recommendation.vm_id,
        source: recommendation.source_node || 'unknown',
        target: recommendation.target_node,
        progress: 0,
        state: 'RECOMMENDED'
      }
    : null;

  const filteredVms = vms.filter((vm) => {
    if (filterSla !== 'all' && vm.sla_priority !== filterSla) return false;
    return true;
  });

  return (
    <div className="relative w-full rounded-xl border border-[#1C202A] bg-[#07090E] p-6 sm:p-8 shadow-2xl overflow-hidden">
      {/* Background Architectural Grid Pattern */}
      <div 
        className="pointer-events-none absolute inset-0 opacity-[0.03]" 
        style={{
          backgroundImage: 'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}
      />

      {/* Top Header & Interconnect Controls */}
      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#1C202A] pb-5 mb-6">
        <div>
          <div className="flex items-center space-x-2 text-blue-400 font-mono text-xs mb-1">
            <Network className="h-4 w-4" />
            <span className="tracking-widest uppercase">02 // COMPUTE FABRIC & TOPOLOGY MESH</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-light text-white uppercase tracking-tight">
            Spatial Hypervisor Chassis & Workload Mesh
          </h2>
          <p className="font-mono text-xs text-[#6B7280] mt-0.5">
            Physical compute node telemetry, vCPU/memory allocation bounds, and real-time interconnect migration vectors
          </p>
        </div>

        {/* SLA Filters & Topology Stats */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          <div className="flex items-center space-x-1.5 rounded border border-[#1C202A] bg-[#0E1015] px-3 py-1.5 text-[#9CA3AF]">
            <span className="text-[#6B7280]">NODES:</span>
            <span className="text-white font-bold">{nodes.length}</span>
            <span className="text-[#4B5563]">|</span>
            <span className="text-[#6B7280]">VMS:</span>
            <span className="text-white font-bold">{vms.length}</span>
          </div>

          <div className="flex items-center space-x-1 rounded border border-[#1C202A] bg-[#0E1015] p-1">
            <span className="text-[#6B7280] px-2 text-[10px] uppercase">SLA:</span>
            {['all', 'critical', 'high', 'standard', 'batch'].map((tier) => (
              <button
                key={tier}
                onClick={() => setFilterSla(tier)}
                className={`rounded px-2.5 py-1 uppercase text-[10px] font-semibold transition-all cursor-pointer ${
                  filterSla === tier
                    ? 'border border-[#3D465C] bg-[#1C202A] text-white shadow-sm'
                    : 'text-[#6B7280] hover:text-[#9CA3AF]'
                }`}
              >
                {tier}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Migration Vector Fabric Bar (When Active or Recommended) */}
      {migrationVector && (
        <div className="relative z-10 mb-6 rounded-lg border border-blue-500/30 bg-gradient-to-r from-blue-950/30 via-[#0E131E] to-blue-950/30 p-4 font-mono text-xs shadow-lg">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center space-x-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-md border border-blue-500/40 bg-blue-500/10">
                <Zap className="h-4 w-4 text-blue-400 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    migrationVector.type === 'ACTIVE_MIGRATION'
                      ? 'border border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : 'border border-blue-500/40 bg-blue-500/10 text-blue-300'
                  }`}>
                    {migrationVector.type === 'ACTIVE_MIGRATION' ? 'LIVE HYPERVISOR MIGRATION' : 'CANDIDATE MIGRATION VECTOR'}
                  </span>
                  <span className="text-white font-bold">{migrationVector.vm_id}</span>
                </div>
                <div className="text-[11px] text-[#9CA3AF] mt-0.5 flex items-center space-x-2">
                  <span>SOURCE: <strong className="text-amber-300">{migrationVector.source.toUpperCase()}</strong></span>
                  <ArrowRight className="h-3 w-3 text-blue-400 inline" />
                  <span>TARGET: <strong className="text-emerald-300">{migrationVector.target.toUpperCase()}</strong></span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-[#6B7280] text-[11px]">STATE:</span>
              <span className="rounded bg-[#14171E] border border-[#2A303F] px-2.5 py-1 text-white font-semibold uppercase text-[11px]">
                {migrationVector.state}
              </span>
              {migrationVector.type === 'ACTIVE_MIGRATION' && (
                <span className="text-blue-400 font-bold">{migrationVector.progress.toFixed(0)}%</span>
              )}
            </div>
          </div>

          {migrationVector.type === 'ACTIVE_MIGRATION' && (
            <div className="w-full bg-[#050608] h-1.5 rounded-full overflow-hidden border border-[#1C202A]">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 via-indigo-400 to-emerald-400 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.6)]"
                style={{ width: `${migrationVector.progress}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Spatial Compute Chassis Grid */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {nodes.map((node, index) => {
          const hostedVMs = filteredVms.filter((v) => v.node_id === node.id);
          const isHot = node.cpu_percent > 75.0;
          const isSelected = selectedNode?.id === node.id;
          const isTarget = migrationVector?.target === node.id;
          const isSource = migrationVector?.source === node.id;
          const nodeProfile = telemetry?.node_profiles?.[node.id];

          return (
            <div
              key={node.id}
              onClick={() => setSelectedNode(isSelected ? null : node)}
              className={`relative rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden ${
                isSelected
                  ? 'border-blue-500 bg-[#0F131D] shadow-[0_0_30px_rgba(59,130,246,0.18)] ring-1 ring-blue-500/40'
                  : isTarget
                  ? 'border-emerald-500/60 bg-[#0B1218] shadow-[0_0_20px_rgba(16,185,129,0.12)]'
                  : isSource
                  ? 'border-amber-500/60 bg-[#14110C] shadow-[0_0_20px_rgba(245,158,11,0.12)]'
                  : 'border-[#1C202A] bg-[#0A0C11] hover:border-[#2E364A] hover:bg-[#0C0F16]'
              }`}
            >
              {/* Chassis Accent Top Border */}
              <div className={`h-1 w-full ${
                isTarget 
                  ? 'bg-emerald-500' 
                  : isSource 
                  ? 'bg-amber-500' 
                  : isHot 
                  ? 'bg-red-500' 
                  : 'bg-[#1C202A]'
              }`} />

              <div className="p-5">
                {/* Server Chassis Header */}
                <div className="flex items-center justify-between border-b border-[#1C202A] pb-3 mb-4 font-mono text-xs">
                  <div className="flex items-center space-x-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
                      node.status === 'online' 
                        ? (isHot ? 'border-amber-500/40 bg-amber-500/10' : 'border-[#2A303F] bg-[#12151D]') 
                        : 'border-red-500/40 bg-red-500/10'
                    }`}>
                      <Server className={`h-4 w-4 ${
                        node.status === 'online' 
                          ? (isHot ? 'text-amber-400' : 'text-blue-400') 
                          : 'text-red-400'
                      }`} />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white tracking-wider text-sm">{node.id.toUpperCase()}</span>
                        <span className="text-[10px] text-[#6B7280] font-mono">RU-0{index + 1}</span>
                      </div>
                      <div className="text-[10px] text-[#9CA3AF]">{node.name}</div>
                    </div>
                  </div>

                  <div className="text-right flex flex-col items-end">
                    <div className="flex items-center space-x-1.5">
                      <span className={`inline-block h-2 w-2 rounded-full ${
                        node.status === 'online' ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]' : 'bg-red-500'
                      }`} />
                      <span className="text-[10px] font-bold uppercase text-white">{node.status}</span>
                    </div>
                    {isTarget && (
                      <span className="text-[9px] font-mono text-emerald-400 font-semibold mt-0.5">TARGET HOST</span>
                    )}
                    {isSource && (
                      <span className="text-[9px] font-mono text-amber-400 font-semibold mt-0.5">SOURCE HOST</span>
                    )}
                  </div>
                </div>

                {/* Node Telemetry Gauges */}
                <div className="space-y-3 mb-5 font-mono text-xs">
                  {/* CPU Load Gauge */}
                  <div>
                    <div className="flex justify-between items-center text-[11px] mb-1.5">
                      <span className="text-[#9CA3AF] flex items-center space-x-1.5">
                        <Cpu className="h-3 w-3 text-[#6B7280]" />
                        <span>CPU UTILIZATION</span>
                        {nodeProfile && (
                          <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                            nodeProfile.cpu_trend === 'rising'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : nodeProfile.cpu_trend === 'falling'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}>
                            {nodeProfile.cpu_trend.toUpperCase()}
                          </span>
                        )}
                      </span>
                      <span className={`font-semibold ${isHot ? 'text-amber-400 font-bold' : 'text-white'}`}>
                        {node.cpu_percent.toFixed(1)}% 
                        {nodeProfile && (
                          <span className="text-[#6B7280] font-normal text-[10px] ml-1">
                            (avg {nodeProfile.cpu_moving_avg.toFixed(1)}%)
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-[#050608] rounded-full overflow-hidden border border-[#14171E]">
                      <div
                        className={`h-full transition-all duration-500 ${
                          isHot 
                            ? 'bg-gradient-to-r from-amber-500 to-red-500' 
                            : 'bg-gradient-to-r from-blue-600 to-blue-400'
                        }`}
                        style={{ width: `${Math.min(100, node.cpu_percent)}%` }}
                      />
                    </div>
                  </div>

                  {/* RAM Allocation Gauge */}
                  <div>
                    <div className="flex justify-between text-[11px] mb-1.5">
                      <span className="text-[#9CA3AF] flex items-center space-x-1.5">
                        <HardDrive className="h-3 w-3 text-[#6B7280]" />
                        <span>MEMORY ALLOCATED</span>
                      </span>
                      <span className="text-white font-semibold">
                        {node.ram_percent.toFixed(1)}% 
                        <span className="text-[#6B7280] font-normal text-[10px] ml-1">
                          ({(node.ram_used_mb / 1024).toFixed(1)} / {(node.ram_total_mb / 1024).toFixed(0)} GB)
                        </span>
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-[#050608] rounded-full overflow-hidden border border-[#14171E]">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all duration-500"
                        style={{ width: `${Math.min(100, node.ram_percent)}%` }}
                      />
                    </div>
                  </div>

                  {/* Network & Disk Telemetry Strip */}
                  <div className="flex items-center justify-between text-[10px] text-[#6B7280] pt-2 border-t border-[#14171E]">
                    <span>NET: {((node.net_rx_kbps + node.net_tx_kbps) / 1024).toFixed(1)} MB/s</span>
                    <span>DISK: {node.disk_used_gb.toFixed(0)} / {node.disk_total_gb.toFixed(0)} GB</span>
                    <span>CORES: {node.cpu_cores || 8} vCPU</span>
                  </div>
                </div>

                {/* Hosted Virtual Machines Shelf */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between font-mono text-[10px] text-[#6B7280] uppercase tracking-wider">
                    <span>HOSTED WORKLOADS ({hostedVMs.length})</span>
                    <span>CLICK TO INSPECT</span>
                  </div>

                  <div className="space-y-2">
                    {hostedVMs.map((vm) => {
                      const isVmSelected = selectedVm?.vmid === vm.vmid;
                      const isMigrating = vm.status === 'migrating';
                      const isCandidate = migrationVector?.vm_id === vm.vmid;

                      return (
                        <div
                          key={vm.vmid}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedVm(isVmSelected ? null : vm);
                          }}
                          className={`rounded-lg border p-3 transition-all cursor-pointer ${
                            isVmSelected
                              ? 'border-blue-400 bg-[#161B26] shadow-md ring-1 ring-blue-400/40'
                              : isMigrating
                              ? 'border-amber-500/60 bg-amber-500/10 animate-pulse'
                              : isCandidate
                              ? 'border-blue-500/40 bg-blue-500/10'
                              : 'border-[#1C202A] bg-[#0E1015] hover:border-[#2D3548] hover:bg-[#12151D]'
                          }`}
                        >
                          <div className="flex items-center justify-between font-mono text-xs mb-1.5">
                            <div className="flex items-center space-x-2">
                              <span className={`h-2 w-2 rounded-full ${
                                isMigrating ? 'bg-amber-400 animate-ping' : 'bg-emerald-400'
                              }`} />
                              <span className="font-bold text-white tracking-wide">{vm.vmid}</span>
                              <span className="text-[10px] text-[#6B7280]">({vm.name})</span>
                            </div>

                            <span className={`text-[9px] px-2 py-0.5 rounded font-mono uppercase font-semibold ${
                              vm.sla_priority === 'critical'
                                ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                                : vm.sla_priority === 'high'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-[#181D28] text-[#9CA3AF] border border-[#222838]'
                            }`}>
                              {vm.sla_priority}
                            </span>
                          </div>

                          <div className="flex items-center justify-between font-mono text-[10px] text-[#9CA3AF]">
                            <span>CPU: <strong className="text-white">{vm.cpu_percent.toFixed(1)}%</strong></span>
                            <span>RAM: <strong className="text-white">{(vm.ram_allocated_mb / 1024).toFixed(1)} GB</strong></span>
                            <span className="text-[#6B7280]">MIGS: {vm.migration_count}</span>
                          </div>
                        </div>
                      );
                    })}

                    {hostedVMs.length === 0 && (
                      <div className="rounded-lg border border-dashed border-[#1C202A] p-4 text-center font-mono text-xs text-[#4B5563]">
                        No active workloads placed on this node.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected VM Deep Telemetry Drawer */}
      {selectedVm && (
        <div className="relative z-10 mt-6 rounded-xl border border-blue-500/40 bg-[#0E121B] p-5 font-mono text-xs shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#1C202A] pb-3 mb-4">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded border border-blue-500/40 bg-blue-500/10">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
              </div>
              <span className="font-bold text-white text-sm">
                WORKLOAD DEEP TELEMETRY INSPECTOR: {selectedVm.vmid} ({selectedVm.name})
              </span>
            </div>
            <button
              onClick={() => setSelectedVm(null)}
              className="rounded p-1 text-[#6B7280] hover:text-white hover:bg-[#1C202A] transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 mb-4">
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">HOST COMPUTE NODE</div>
              <div className="text-white font-bold text-sm mt-0.5">{selectedVm.node_id.toUpperCase()}</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">CPU ALLOCATION</div>
              <div className="text-white font-bold text-sm mt-0.5">{selectedVm.cpu_percent.toFixed(1)}% ({selectedVm.cpu_cores} vCPU)</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">RAM RESERVATION</div>
              <div className="text-white font-bold text-sm mt-0.5">{(selectedVm.ram_allocated_mb / 1024).toFixed(1)} GB</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">SLA LEVEL / CEILING</div>
              <div className="text-amber-400 font-bold text-sm mt-0.5">{selectedVm.sla_priority.toUpperCase()} ({selectedVm.sla_max_cpu_percent}%)</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">DIRTY PAGE RATE (EST)</div>
              <div className="text-indigo-300 font-bold text-sm mt-0.5">~{Math.round(selectedVm.cpu_percent * 1.8)} MB/s</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">MIGRATION COOLDOWN</div>
              <div className="text-emerald-400 font-bold text-sm mt-0.5">
                {selectedVm.last_migrated_at && (Date.now() / 1000 - selectedVm.last_migrated_at < 60)
                  ? `${Math.round(60 - (Date.now() / 1000 - selectedVm.last_migrated_at))}s REMAINING`
                  : 'READY (SATISFIED)'}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-[#9CA3AF] border-t border-[#1C202A] pt-3">
            <span>UPTIME: {Math.floor(selectedVm.uptime_seconds / 86400)}d {Math.floor((selectedVm.uptime_seconds % 86400) / 3600)}h {Math.floor((selectedVm.uptime_seconds % 3600) / 60)}m</span>
            <span>LAST MIGRATION TIMESTAMP: {selectedVm.last_migrated_at ? `${new Date(selectedVm.last_migrated_at * 1000).toLocaleTimeString()}` : 'None (Boot placement)'}</span>
            <span>LIFETIME MIGRATIONS: {selectedVm.migration_count}</span>
          </div>
        </div>
      )}

      {/* Selected Node Deep Telemetry Drawer */}
      {selectedNode && (
        <div className="relative z-10 mt-6 rounded-xl border border-indigo-500/40 bg-[#0E1018] p-5 font-mono text-xs shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#1C202A] pb-3 mb-4">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded border border-indigo-500/40 bg-indigo-500/10">
                <Gauge className="h-3.5 w-3.5 text-indigo-400" />
              </div>
              <span className="font-bold text-white text-sm">
                COMPUTE NODE HARDWARE TELEMETRY: {selectedNode.id.toUpperCase()} ({selectedNode.name})
              </span>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="rounded p-1 text-[#6B7280] hover:text-white hover:bg-[#1C202A] transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">HYPERVISOR STATE</div>
              <div className="text-emerald-400 font-bold text-sm mt-0.5 uppercase">{selectedNode.status}</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">CPU CORES / TOPOLOGY</div>
              <div className="text-white font-bold text-sm mt-0.5">{selectedNode.cpu_cores || 8} vCPUs (1 Socket)</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">TOTAL INSTALLED MEMORY</div>
              <div className="text-white font-bold text-sm mt-0.5">{(selectedNode.ram_total_mb / 1024).toFixed(0)} GB ECC DDR4</div>
            </div>
            <div className="rounded border border-[#1C202A] bg-[#08090C] p-3">
              <div className="text-[#6B7280] text-[10px]">STORAGE ATTACHMENT</div>
              <div className="text-white font-bold text-sm mt-0.5">{selectedNode.disk_used_gb.toFixed(0)} / {selectedNode.disk_total_gb.toFixed(0)} GB (NFSv4 / ZFS)</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
