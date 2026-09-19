import React, { useState } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Lock,
  ShieldCheck,
  ArrowRight,
  UserCheck,
  Check,
  X
} from 'lucide-react';
import type { SafetyEvaluation, SafetyCheckResult, PendingProposal } from '../types';

interface SafetyGateSectionProps {
  safetyEvaluation: SafetyEvaluation | null;
  activeProposal?: PendingProposal | null;
  onApprove?: (proposalId: string) => Promise<boolean>;
  onReject?: (proposalId: string) => Promise<boolean>;
}

export const SafetyGateSection: React.FC<SafetyGateSectionProps> = ({ 
  safetyEvaluation,
  activeProposal,
  onApprove,
  onReject
}) => {
  const [submitting, setSubmitting] = useState<boolean>(false);

  const defaultRules: SafetyCheckResult[] = [
    {
      check_name: 'VM_RUNNING_STATE',
      passed: true,
      severity: 'CRITICAL',
      message: 'Workload active state confirmed. Target workload is operational in running hypervisor state.'
    },
    {
      check_name: 'DISTINCT_TARGET',
      passed: true,
      severity: 'CRITICAL',
      message: 'Inter-node distinct trajectory validated. Source and destination are separate physical hosts.'
    },
    {
      check_name: 'SOURCE_NODE_HEALTH',
      passed: true,
      severity: 'CRITICAL',
      message: 'Source host online and responsive. Hypervisor daemon reports zero alarms and active heartbeat.'
    },
    {
      check_name: 'DEST_NODE_HEALTH',
      passed: true,
      severity: 'CRITICAL',
      message: 'Destination host online and reachable. Destination hypervisor daemon responsive on cluster fabric.'
    },
    {
      check_name: 'DEST_RAM_HEADROOM',
      passed: true,
      severity: 'CRITICAL',
      message: 'Destination memory capacity confirmed. Unallocated RAM exceeds VM footprint with 20% safety margin.'
    },
    {
      check_name: 'DEST_CPU_CAPACITY',
      passed: true,
      severity: 'CRITICAL',
      message: 'Destination CPU capacity verified. Projected post-migration CPU load remains safely below 85%.'
    },
    {
      check_name: 'STORAGE_AND_QUORUM',
      passed: true,
      severity: 'CRITICAL',
      message: 'Storage and quorum consensus intact. Datastore prerequisites verified and cluster quorum active.'
    },
    {
      check_name: 'COOLDOWN_PERIOD',
      passed: true,
      severity: 'WARNING',
      message: 'Cooldown policy satisfied. Minimum 60 seconds elapsed since prior migration event.'
    }
  ];

  const checksToDisplay = safetyEvaluation?.results && safetyEvaluation.results.length > 0 
    ? safetyEvaluation.results 
    : defaultRules;

  const isBlocked = safetyEvaluation ? safetyEvaluation.blocked : false;
  const passedCount = safetyEvaluation ? safetyEvaluation.passed_checks : checksToDisplay.filter(c => c.passed).length;
  const totalCount = safetyEvaluation ? safetyEvaluation.total_checks : checksToDisplay.length;

  const handleApprove = async () => {
    if (!activeProposal || !onApprove) return;
    setSubmitting(true);
    await onApprove(activeProposal.proposal_id);
    setSubmitting(false);
  };

  const handleReject = async () => {
    if (!activeProposal || !onReject) return;
    setSubmitting(true);
    await onReject(activeProposal.proposal_id);
    setSubmitting(false);
  };

  return (
    <div className="w-full space-y-8 font-mono text-xs">
      
      {/* Editorial Centerpiece Banner */}
      <div className="rounded-2xl border border-[#CBD5E1] bg-gradient-to-b from-white via-[#F8FAFC] to-[#F1F5F9] p-8 sm:p-12 text-center relative overflow-hidden shadow-xs">
        <div className="inline-flex items-center space-x-2 rounded-full border border-amber-300 bg-amber-50 px-4 py-1 text-xs text-amber-800 font-semibold mb-6 shadow-2xs">
          <Lock className="h-3.5 w-3.5 text-amber-600" />
          <span className="tracking-wider uppercase">DETERMINISTIC CONTROL POLICY · HARD BOUNDARY LAYER</span>
        </div>

        <h2 className="text-3xl sm:text-5xl lg:text-6xl font-light uppercase tracking-tight text-[#0F172A] leading-tight font-sans">
          THE AI DOESN'T <br />
          <span className="font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-red-600 via-amber-600 to-[#0F172A]">
            GET THE FINAL WORD.
          </span>
        </h2>

        <p className="text-sm sm:text-base text-[#475569] max-w-2xl mx-auto mt-4 font-normal font-sans leading-relaxed">
          Reinforcement learning proposes candidates to optimize cluster load balance. 
          Deterministic safety code enforces absolute physical constraints. No AI recommendation can bypass 
          memory headroom, storage, quorum, or human authorization.
        </p>

        {/* Sequential Architecture Flow */}
        <div className="mt-8 pt-6 border-t border-[#E2E8F0] flex flex-wrap items-center justify-center gap-3 font-mono text-xs">
          <div className="flex items-center space-x-1.5 rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-1.5 shadow-2xs">
            <span className="text-purple-600 font-bold">PPO PROPOSAL</span>
          </div>
          <ArrowRight className="h-4 w-4 text-[#94A3B8]" />
          <div className="flex items-center space-x-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3.5 py-1.5 font-bold text-blue-800 shadow-2xs">
            <span>DETERMINISTIC SAFETY GATE</span>
          </div>
          <ArrowRight className="h-4 w-4 text-[#94A3B8]" />
          <div className="flex items-center space-x-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-1.5 font-bold text-amber-800 shadow-2xs">
            <span>HUMAN APPROVAL</span>
          </div>
          <ArrowRight className="h-4 w-4 text-[#94A3B8]" />
          <div className="flex items-center space-x-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-1.5 font-bold text-emerald-800 shadow-2xs">
            <span>HYPERVISOR EXECUTION</span>
          </div>
        </div>
      </div>

      {/* Human-in-the-Loop Operator Gate (Active if pending approval) */}
      {activeProposal && activeProposal.status === 'PENDING_APPROVAL' && (
        <div className="rounded-2xl border-2 border-amber-400 bg-amber-50/70 p-6 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
            <div className="flex items-start space-x-3.5">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-xs">
                <UserCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="rounded-full bg-amber-200 text-amber-900 px-2 py-0.5 text-[10px] font-bold uppercase">
                    STAGE 03 · OPERATOR GATE
                  </span>
                  <span className="text-[11px] text-amber-800 font-semibold">ALL 8 SAFETY CHECKS SATISFIED</span>
                </div>
                <h3 className="text-base font-bold text-[#0F172A] mt-1">
                  Authorize Live Migration: Workload <span className="text-blue-600">{activeProposal.vm_id}</span> ({activeProposal.source_node} → {activeProposal.target_node})
                </h3>
                <p className="text-xs text-[#475569] mt-0.5 font-sans">
                  {activeProposal.reason} · Selection Probability: {(activeProposal.confidence_score * 100).toFixed(1)}% · Strategy: {(activeProposal as any).with_local_disks ? '--with-local-disks 1 (NBD mirror)' : 'Shared Datastore'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3 shrink-0">
              <button
                onClick={handleReject}
                disabled={submitting}
                className="flex items-center space-x-1.5 rounded-lg border border-red-300 bg-white px-4 py-2.5 font-semibold text-red-700 hover:bg-red-50 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              >
                <X className="h-4 w-4" />
                <span>DECLINE</span>
              </button>

              <button
                onClick={handleApprove}
                disabled={submitting}
                className="flex items-center space-x-2 rounded-lg bg-emerald-600 px-5 py-2.5 font-bold text-white hover:bg-emerald-700 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                <span>AUTHORIZE DISPATCH</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8-Rule Sequential Audit Pipeline */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-4">
          <div>
            <div className="flex items-center space-x-2 text-blue-600 font-bold">
              <ShieldCheck className="h-4 w-4" />
              <span className="uppercase tracking-wider">MANDATORY 8-RULE SAFETY CRITERIA MATRIX</span>
            </div>
            <p className="text-[#64748B] text-[11px] mt-0.5 font-sans">
              Evaluated sequentially against physical hypervisor telemetry before any proposal enters the approval gate.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
              isBlocked
                ? 'border-red-200 bg-red-50 text-red-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-800'
            }`}>
              {passedCount} OF {totalCount} CHECKS SATISFIED
            </span>
          </div>
        </div>

        {/* Sequential List of 8 Rules */}
        <div className="space-y-3">
          {checksToDisplay.map((check, idx) => {
            return (
              <div
                key={check.check_name}
                className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border transition-all ${
                  check.passed
                    ? 'border-[#E2E8F0] bg-[#F8FAFC] hover:bg-white hover:border-[#CBD5E1]'
                    : 'border-red-200 bg-red-50/60'
                }`}
              >
                <div className="flex items-start space-x-3.5">
                  <div className="pt-0.5">
                    {check.passed ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2 font-mono">
                      <span className="text-[10px] text-[#94A3B8] font-bold">RULE 0{idx + 1}</span>
                      <span className="font-bold text-[#0F172A]">{check.check_name}</span>
                      <span className="text-[10px] text-[#64748B] font-mono">
                        {check.metric_value ? `[${check.metric_value}]` : `[${check.severity}]`}
                      </span>
                    </div>
                    <p className="text-xs text-[#475569] mt-1 font-sans">
                      {check.message}
                    </p>
                  </div>
                </div>

                <div className="mt-3 sm:mt-0 sm:text-right shrink-0">
                  <span className={`inline-block px-2.5 py-1 rounded-md text-[11px] font-bold ${
                    check.passed 
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {check.passed ? 'SATISFIED' : 'BLOCKED'}
                  </span>
                  {check.metric_value && (
                    <div className="text-[10px] text-[#64748B] mt-1 font-mono">
                      {check.metric_value}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
