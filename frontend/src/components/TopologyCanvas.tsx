import React, { useState } from 'react';
import { 
  Server, 
  Cpu, 
  Zap, 
  Network,
  X
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
  selectedEntityId?: string | null;
  onClearSelection?: () => void;
}

export const TopologyCanvas: React.FC<TopologyCanvasProps> = ({
  cluster,
  activeTasks,
  recommendation
}) => {
  const [selectedVm, setSelectedVm] = useState<VMTelemetry | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeTelemetry | null>(null);
  const [filterSla, setFilterSla] = useState<string>('all');

  const nodes = cluster ? Object.values(cluster.nodes) : [];
  const vms = cluster ? Object.values(cluster.vms) : [];

  const isSim = !cluster || cluster.provider_name === 'simulation';
  const isDisconnected = cluster && cluster.is_live && !cluster.connected;

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
    <div className="relative w-full rounded-2xl border border-[#E2E8F0] bg-white p-6 sm:p-8 shadow-xs">
      
      {/* Top Header & Interconnect Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-6 mb-8">
        <div>
          <div className="flex items-center space-x-2 text-blue-600 font-mono text-xs mb-1 font-bold tracking-wider">
            <Network className="h-4 w-4" />
            <span className="uppercase">02 // COMPUTE FABRIC & WORKLOAD MESH</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-light text-[#0F172A] uppercase tracking-tight">
            Spatial Hypervisor Chassis & Workloads
          </h2>
          <p className="font-mono text-xs text-[#64748B] mt-1">
            Physical compute node telemetry, vCPU/memory allocation bounds, and real-time interconnect migration vectors.
          </p>
        </div>

        {/* Environment Truthfulness Banner */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {isDisconnected ? (
            <div className="flex items-center space-x-2 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-red-700">
              <span className="h-2 w-2 rounded-full bg-red-600 animate-ping" />
              <span className="font-semibold">LIVE / PROXMOX DISCONNECTED</span>
            </div>
          ) : isSim ? (
            <div className="flex items-center space-x-2 rounded-lg border border-slate-200 bg-[#F8FAFC] px-3 py-1.5 text-[#475569]">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>SIMULATION · <strong className="text-[#0F172A]">SYNTHETIC CLUSTER</strong></span>
            </div>
          ) : (
            <div className="flex items-center space-x-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-emerald-800">
              <span className="h-2 w-2 rounded-full bg-emerald-600" />
              <span>LIVE · <strong className="text-emerald-900">{cluster?.provider_name.toUpperCase()}</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* Migration Vector Banner (if migrating or recommended) */}
      {migrationVector && (
        <div className="mb-8 rounded-xl border border-blue-200 bg-blue-50/50 p-4 font-mono text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
                <Zap className="h-4 w-4" />
              </div>
              <div>
                <span className="font-bold text-blue-900">
                  {migrationVector.type === 'ACTIVE_MIGRATION' ? 'ACTIVE LIVE MIGRATION CONDUIT' : 'RECOMMENDED MIGRATION VECTOR'}
                </span>
                <div className="text-[#475569] text-[11px] mt-0.5">
                  Workload <strong className="text-[#0F172A]">{migrationVector.vm_id}</strong>: {migrationVector.source} → {migrationVector.target}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="rounded-full border border-blue-300 bg-white px-3 py-1 text-[11px] font-semibold text-blue-700">
                STATE: {migrationVector.state}
              </span>
              {migrationVector.progress > 0 && (
                <span className="rounded-full border border-emerald-300 bg-white px-3 py-1 text-[11px] font-semibold text-emerald-700">
                  {migrationVector.progress.toFixed(0)}% COMPLETE
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SLA Priority Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 font-mono text-xs mb-6 pb-4 border-b border-[#E2E8F0]">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] text-[#64748B] font-semibold uppercase">FILTER SLA PRIORITY:</span>
          {['all', 'critical', 'high', 'standard', 'batch'].map((sla) => (
            <button
              key={sla}
              onClick={() => setFilterSla(sla)}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
                filterSla === sla
                  ? 'bg-[#0F172A] text-white font-semibold shadow-2xs'
                  : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
              }`}
            >
              {sla.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="text-[#64748B] text-[11px]">
          Showing {filteredVms.length} of {vms.length} workloads across {nodes.length} hosts
        </div>
      </div>

      {/* Compute Hosts (Node Chassis Grid) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {nodes.map((node) => {
          const nodeVms = filteredVms.filter((v) => v.node_id === node.id);
          const isTargetInMigration = migrationVector?.target === node.id;
          const isSourceInMigration = migrationVector?.source === node.id;

          return (
            <div
              key={node.id}
              onClick={() => setSelectedNode(node)}
              className={`rounded-xl border p-5 transition-all cursor-pointer bg-white ${
                isTargetInMigration
                  ? 'border-emerald-400 ring-2 ring-emerald-400/20 shadow-sm'
                  : isSourceInMigration
                  ? 'border-blue-400 ring-2 ring-blue-400/20 shadow-sm'
                  : 'border-[#E2E8F0] hover:border-[#CBD5E1] shadow-2xs hover:shadow-xs'
              }`}
            >
              {/* Host Header */}
              <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
                <div className="flex items-center space-x-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-[#F1F5F9] text-[#0F172A]">
                    <Server className="h-4 w-4" />
                  </div>
                  <div>
                    <span className="font-mono text-xs font-bold text-[#0F172A]">{node.id}</span>
                    <span className="block text-[10px] text-[#64748B] font-mono">{node.name}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 font-mono text-[10px]">
                  <span className={`h-2 w-2 rounded-full ${node.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  <span className={node.status === 'online' ? 'text-emerald-700 font-semibold' : 'text-red-700 font-semibold'}>
                    {node.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Node Telemetry Gauges */}
              <div className="grid grid-cols-2 gap-3 my-4 font-mono text-xs">
                {/* CPU Bar */}
                <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2.5">
                  <div className="flex justify-between text-[10px] text-[#64748B]">
                    <span>CPU LOAD</span>
                    <span className="font-bold text-[#0F172A]">{node.cpu_percent}%</span>
                  </div>
                  <div className="w-full bg-[#E2E8F0] h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        node.cpu_percent > 85 ? 'bg-red-600' : node.cpu_percent > 65 ? 'bg-amber-500' : 'bg-blue-600'
                      }`}
                      style={{ width: `${Math.min(100, node.cpu_percent)}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-[#94A3B8] mt-1.5">{node.cpu_cores} vCPU Cores</div>
                </div>

                {/* RAM Bar */}
                <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-2.5">
                  <div className="flex justify-between text-[10px] text-[#64748B]">
                    <span>RAM USAGE</span>
                    <span className="font-bold text-[#0F172A]">{node.ram_percent}%</span>
                  </div>
                  <div className="w-full bg-[#E2E8F0] h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className="h-full bg-purple-600 transition-all"
                      style={{ width: `${Math.min(100, node.ram_percent)}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-[#94A3B8] mt-1.5">
                    {(node.ram_used_mb / 1024).toFixed(1)} / {(node.ram_total_mb / 1024).toFixed(0)} GB
                  </div>
                </div>
              </div>

              {/* Status Pills: Quorum & Storage */}
              <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] pb-3 border-b border-[#E2E8F0]">
                <span className={`px-2 py-0.5 rounded border ${
                  node.quorum_healthy ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'
                }`}>
                  QUORUM: {node.quorum_healthy ? 'HEALTHY' : 'LOST'}
                </span>
                <span className={`px-2 py-0.5 rounded border ${
                  node.shared_storage_accessible ? 'border-blue-200 bg-blue-50 text-blue-800' : 'border-slate-200 bg-slate-50 text-slate-700'
                }`}>
                  SHARED STORAGE: {node.shared_storage_accessible ? 'ACCESSIBLE' : 'LOCAL ONLY'}
                </span>
              </div>

              {/* Hosted Workloads Slots */}
              <div className="mt-4">
                <div className="text-[10px] font-mono text-[#64748B] font-bold uppercase mb-2">
                  Hosted Workloads ({nodeVms.length}):
                </div>

                <div className="space-y-1.5">
                  {nodeVms.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-[#CBD5E1] p-3 text-center text-[11px] font-mono text-[#94A3B8]">
                      Zero workloads running on host
                    </div>
                  ) : (
                    nodeVms.map((vm) => {
                      const isCandidate = migrationVector?.vm_id === vm.vmid;
                      return (
                        <div
                          key={vm.vmid}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedVm(vm);
                          }}
                          className={`flex items-center justify-between rounded-lg border p-2.5 font-mono text-xs transition-all ${
                            isCandidate
                              ? 'border-blue-400 bg-blue-50/60 shadow-xs'
                              : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#CBD5E1] hover:bg-white'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                            <div>
                              <span className="font-bold text-[#0F172A]">{vm.vmid}</span>
                              <span className="text-[10px] text-[#64748B] ml-1.5 font-normal">({vm.name})</span>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 text-[10px]">
                            <span className={`px-1.5 py-0.5 rounded uppercase font-semibold ${
                              vm.sla_priority === 'critical'
                                ? 'bg-purple-100 text-purple-800'
                                : vm.sla_priority === 'high'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}>
                              {vm.sla_priority}
                            </span>
                            <span className="text-[#0F172A] font-semibold">{vm.cpu_percent}%</span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected VM Metadata Modal / Drawer */}
      {selectedVm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4 mb-4">
              <div className="flex items-center space-x-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-200">
                  <Cpu className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#0F172A]">{selectedVm.name}</h3>
                  <span className="text-[11px] text-[#64748B]">VMID: {selectedVm.vmid} · HOST: {selectedVm.node_id}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedVm(null)}
                className="rounded-lg p-1.5 text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-5">
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">STATUS</span>
                <div className="text-sm font-bold text-emerald-700 mt-1 uppercase">{selectedVm.status}</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">SLA PRIORITY</span>
                <div className="text-sm font-bold text-purple-700 mt-1 uppercase">{selectedVm.sla_priority}</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">CPU UTILIZATION</span>
                <div className="text-sm font-bold text-[#0F172A] mt-1">{selectedVm.cpu_percent}% ({selectedVm.cpu_cores} vCPUs)</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">MEMORY ALLOCATION</span>
                <div className="text-sm font-bold text-[#0F172A] mt-1">{selectedVm.ram_used_mb} / {selectedVm.ram_allocated_mb} MB</div>
              </div>
            </div>

            <div className="space-y-2 text-[11px] text-[#475569] border-t border-[#E2E8F0] pt-4">
              <div className="flex justify-between">
                <span>Total Migrations Executed:</span>
                <span className="font-bold text-[#0F172A]">{selectedVm.migration_count}</span>
              </div>
              <div className="flex justify-between">
                <span>Uptime Duration:</span>
                <span className="font-bold text-[#0F172A]">{(selectedVm.uptime_seconds / 3600).toFixed(1)} hours</span>
              </div>
              <div className="flex justify-between">
                <span>Disk Allocated:</span>
                <span className="font-bold text-[#0F172A]">{selectedVm.disk_allocated_gb} GB</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedVm(null)}
                className="rounded-lg border border-[#CBD5E1] bg-white px-4 py-2 font-semibold text-[#0F172A] hover:bg-[#F8FAFC]"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Selected Node Metadata Modal / Drawer */}
      {selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4 mb-4">
              <div className="flex items-center space-x-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200">
                  <Server className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#0F172A]">{selectedNode.id}</h3>
                  <span className="text-[11px] text-[#64748B]">{selectedNode.name}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg p-1.5 text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-5">
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">PHYSICAL STATE</span>
                <div className="text-sm font-bold text-emerald-700 mt-1 uppercase">{selectedNode.status}</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">COROSYNC QUORUM</span>
                <div className="text-sm font-bold text-emerald-700 mt-1">{selectedNode.quorum_healthy ? 'HEALTHY (1)' : 'LOST (0)'}</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">CPU CAPACITY</span>
                <div className="text-sm font-bold text-[#0F172A] mt-1">{selectedNode.cpu_percent}% ({selectedNode.cpu_cores} Cores)</div>
              </div>
              <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <span className="text-[10px] text-[#64748B] uppercase font-semibold">MEMORY CAPACITY</span>
                <div className="text-sm font-bold text-[#0F172A] mt-1">{(selectedNode.ram_used_mb / 1024).toFixed(1)} / {(selectedNode.ram_total_mb / 1024).toFixed(0)} GB</div>
              </div>
            </div>

            <div className="space-y-2 text-[11px] text-[#475569] border-t border-[#E2E8F0] pt-4">
              <div className="flex justify-between">
                <span>Active Workloads Hosted:</span>
                <span className="font-bold text-[#0F172A]">{selectedNode.active_vms.length}</span>
              </div>
              <div className="flex justify-between">
                <span>Shared Datastore Accessibility:</span>
                <span className="font-bold text-[#0F172A]">{selectedNode.shared_storage_accessible ? 'Available' : 'None (Local Disks Only)'}</span>
              </div>
              <div className="flex justify-between">
                <span>Disk Storage Space:</span>
                <span className="font-bold text-[#0F172A]">{selectedNode.disk_used_gb} / {selectedNode.disk_total_gb} GB</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg border border-[#CBD5E1] bg-white px-4 py-2 font-semibold text-[#0F172A] hover:bg-[#F8FAFC]"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
