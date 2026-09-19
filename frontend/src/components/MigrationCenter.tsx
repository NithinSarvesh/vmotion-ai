import React from 'react';
import { 
  Zap, 
  ArrowRight, 
  Activity, 
  XCircle, 
  ShieldCheck,
  Check
} from 'lucide-react';
import type { MigrationTaskStatus } from '../types';

interface MigrationCenterProps {
  activeTasks: MigrationTaskStatus[];
  completedTasks: MigrationTaskStatus[];
}

const FSM_LIFECYCLE_STAGES: { id: string; label: string; num: string }[] = [
  { id: 'RECOMMENDED', label: 'RECOMMENDED', num: '01' },
  { id: 'SAFETY_CHECK', label: 'SAFETY CHECK', num: '02' },
  { id: 'PENDING_APPROVAL', label: 'OPERATOR GATE', num: '03' },
  { id: 'APPROVED', label: 'APPROVED', num: '04' },
  { id: 'DISPATCHED', label: 'DISPATCHED', num: '05' },
  { id: 'TASK_RUNNING', label: 'PRE-COPY / RUNNING', num: '06' },
  { id: 'VERIFYING', label: 'VERIFYING', num: '07' },
  { id: 'VERIFIED', label: 'VERIFIED', num: '08' },
];

export const MigrationCenter: React.FC<MigrationCenterProps> = ({
  activeTasks,
  completedTasks
}) => {
  const activeTask = activeTasks.length > 0 ? activeTasks[0] : null;

  return (
    <div className="w-full space-y-8 font-mono text-xs">
      
      {/* Section Header */}
      <div className="border-b border-[#E2E8F0] pb-6">
        <div className="flex items-center space-x-2 text-cyan-600 text-xs mb-1 font-bold tracking-wider">
          <Zap className="h-4 w-4" />
          <span className="uppercase">05 // MIGRATION ORCHESTRATION & STATE MACHINE</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-light text-[#0F172A] uppercase tracking-tight font-sans">
          8-State Lifecycle & Verification Ledger
        </h2>
        <p className="text-sm text-[#475569] max-w-3xl mt-1 font-normal font-sans">
          Live migrations execute across a strict 8-state deterministic finite state machine (FSM). 
          Tasks are never marked complete upon command dispatch; the control plane actively samples pre-copy iterations, 
          asserts hardware switchover, and verifies QEMU guest agent responsiveness on the destination host.
        </p>
      </div>

      {/* 8-State FSM Progression Overview Bar */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-blue-600" />
            <span className="font-bold text-[#0F172A] tracking-wider uppercase text-xs">
              MIGRATION FINITE STATE MACHINE (FSM) SPECIFICATION
            </span>
          </div>
          <span className="text-[10px] text-[#64748B]">
            DETERMINISTIC TRANSITION GRAPH
          </span>
        </div>

        {/* Progression Pipeline Blocks */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
          {FSM_LIFECYCLE_STAGES.map((stage, idx) => {
            const isCurrentState = activeTask?.state === stage.id;
            return (
              <div 
                key={stage.id} 
                className={`rounded-xl border p-3 text-center relative transition-all ${
                  isCurrentState
                    ? 'border-blue-500 bg-blue-50/70 shadow-xs ring-2 ring-blue-500/20'
                    : 'border-[#E2E8F0] bg-[#F8FAFC]'
                }`}
              >
                <div className="text-[10px] text-[#94A3B8] font-bold">{stage.num}</div>
                <div className={`text-[10px] font-bold mt-1 tracking-tight ${
                  isCurrentState ? 'text-blue-700' : 'text-[#0F172A]'
                }`}>
                  {stage.label}
                </div>
                {idx < 7 && (
                  <ArrowRight className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-[#CBD5E1] z-10" />
                )}
              </div>
            );
          })}
        </div>

        {/* Terminal / Rejection States Strip */}
        <div className="pt-3 border-t border-[#F1F5F9] flex flex-wrap items-center justify-between gap-3 text-[10px]">
          <span className="font-bold text-[#64748B]">TERMINAL & REJECTION STATES:</span>
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-1 rounded-md border border-red-200 bg-red-50 text-red-700 font-bold">
              BLOCKED (Safety Gate)
            </span>
            <span className="px-2.5 py-1 rounded-md border border-amber-200 bg-amber-50 text-amber-800 font-bold">
              REJECTED (Operator Denial)
            </span>
            <span className="px-2.5 py-1 rounded-md border border-red-200 bg-red-50 text-red-700 font-bold">
              FAILED (Hypervisor Error)
            </span>
            <span className="px-2.5 py-1 rounded-md border border-slate-200 bg-slate-100 text-slate-700 font-bold">
              CANCELLED (Operator Abort)
            </span>
          </div>
        </div>
      </div>

      {/* Active Migration Dispatch Queue */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2 text-xs font-bold text-[#0F172A] uppercase tracking-wider">
          <Activity className="h-4 w-4 text-emerald-600" />
          <span>ACTIVE HYPERVISOR DISPATCH QUEUE</span>
        </div>

        {activeTask ? (
          <div className="rounded-2xl border-2 border-blue-400 bg-white p-6 shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-4">
              <div>
                <span className="text-[10px] text-blue-600 font-bold uppercase">DISPATCHED JOB ACTIVE</span>
                <h3 className="text-lg font-bold text-[#0F172A] mt-0.5">
                  Migrating Workload <span className="text-blue-600">{activeTask.vm_id}</span>
                </h3>
                <div className="text-[#64748B] text-xs font-mono mt-0.5">
                  Task UPID: {activeTask.task_id}
                </div>
              </div>

              <span className="rounded-full border border-blue-300 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800">
                STATUS: {activeTask.state}
              </span>
            </div>

            {/* Visual Spatial Conduit Transfer */}
            <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC]">
              <div className="text-center sm:text-left">
                <span className="text-[10px] text-[#64748B] uppercase">SOURCE NODE</span>
                <div className="text-sm font-bold text-[#0F172A]">{activeTask.source_node}</div>
              </div>

              <div className="flex-1 max-w-md px-4 text-center">
                <div className="flex justify-between text-[10px] text-[#64748B] mb-1 font-bold">
                  <span>PRE-COPY MEMORY TRANSFER</span>
                  <span>{activeTask.progress_percent.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-[#E2E8F0] h-2.5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-300"
                    style={{ width: `${Math.max(5, activeTask.progress_percent)}%` }}
                  />
                </div>
              </div>

              <div className="text-center sm:text-right">
                <span className="text-[10px] text-[#64748B] uppercase">DESTINATION HOST</span>
                <div className="text-sm font-bold text-[#0F172A]">{activeTask.target_node}</div>
              </div>
            </div>

            {activeTask.error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700">
                <strong>Dispatch Error:</strong> {activeTask.error}
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-[#CBD5E1] bg-white p-8 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-[#64748B] mb-3">
              <Zap className="h-5 w-5" />
            </div>
            <h4 className="text-sm font-bold text-[#0F172A] uppercase">ZERO ACTIVE MIGRATIONS IN FLIGHT</h4>
            <p className="text-[#64748B] text-xs max-w-md mx-auto mt-1 font-sans">
              No live migration job is currently executing on hypervisor hosts. 
              The control plane is passively sampling cluster telemetry and evaluating policy distributions.
            </p>
          </div>
        )}
      </div>

      {/* Completed Migrations Forensic Archive */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-4">
          <div className="flex items-center space-x-2 text-xs font-bold text-[#0F172A] uppercase tracking-wider">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>POST-MIGRATION PLACEMENT & HEALTH VERIFICATION ARCHIVE</span>
          </div>
          <span className="text-[10px] text-[#64748B]">
            {completedTasks.length} COMPLETED RECORDS
          </span>
        </div>

        {completedTasks.length === 0 ? (
          <div className="p-6 text-center text-[#94A3B8] font-sans text-xs">
            No completed migration records archived in the current session.
          </div>
        ) : (
          <div className="space-y-2.5">
            {completedTasks.slice(0, 5).map((task) => (
              <div 
                key={task.task_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] gap-3"
              >
                <div className="flex items-center space-x-3">
                  <div className={`flex h-6 w-6 items-center justify-center rounded-full ${
                    task.state === 'VERIFIED' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {task.state === 'VERIFIED' ? <Check className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                  </div>
                  <div>
                    <div className="font-bold text-[#0F172A]">
                      Workload {task.vm_id} ({task.source_node} → {task.target_node})
                    </div>
                    <div className="text-[10px] text-[#64748B] mt-0.5">
                      UPID: {task.task_id}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3 text-right">
                  <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold ${
                    task.state === 'VERIFIED' 
                      ? 'bg-emerald-100 text-emerald-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {task.state}
                  </span>
                  {task.verified_at && (
                    <span className="text-[10px] text-[#64748B]">
                      {new Date(task.verified_at * 1000).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
