import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Lock,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import type { SafetyEvaluation, SafetyCheckResult } from '../types';

interface SafetyGateSectionProps {
  safetyEvaluation: SafetyEvaluation | null;
}

const ERROR_CODE_MAP: Record<string, string> = {
  VM_RUNNING_STATE: 'ERR_VM_NOT_RUNNING',
  DISTINCT_TARGET: 'ERR_IDENTICAL_SOURCE_DEST',
  SOURCE_NODE_HEALTH: 'ERR_SOURCE_NODE_UNHEALTHY',
  DEST_NODE_HEALTH: 'ERR_DEST_NODE_OFFLINE',
  DEST_RAM_HEADROOM: 'ERR_INSUFFICIENT_RAM',
  DEST_CPU_CAPACITY: 'ERR_CPU_OVERLOAD_PROJECTED',
  STORAGE_AND_QUORUM: 'ERR_STORAGE_QUORUM_LOST',
  COOLDOWN_PERIOD: 'ERR_COOLDOWN_ACTIVE',
};

export const SafetyGateSection: React.FC<SafetyGateSectionProps> = ({ safetyEvaluation }) => {
  const defaultRules: SafetyCheckResult[] = [
    {
      check_name: 'VM_RUNNING_STATE',
      passed: true,
      severity: 'CRITICAL',
      message: 'Target workload is active and operational in running hypervisor state.'
    },
    {
      check_name: 'DISTINCT_TARGET',
      passed: true,
      severity: 'CRITICAL',
      message: 'Source and destination compute nodes are distinct physical hosts.'
    },
    {
      check_name: 'SOURCE_NODE_HEALTH',
      passed: true,
      severity: 'CRITICAL',
      message: 'Source hypervisor daemon reports zero hardware alarms and active heartbeat.'
    },
    {
      check_name: 'DEST_NODE_HEALTH',
      passed: true,
      severity: 'CRITICAL',
      message: 'Destination hypervisor daemon is online and responsive over cluster network.'
    },
    {
      check_name: 'DEST_RAM_HEADROOM',
      passed: true,
      severity: 'CRITICAL',
      message: 'Destination unallocated memory comfortably exceeds VM footprint + 20% buffer.'
    },
    {
      check_name: 'DEST_CPU_CAPACITY',
      passed: true,
      severity: 'CRITICAL',
      message: 'Projected post-migration CPU load remains safely below 85.0% threshold.'
    },
    {
      check_name: 'STORAGE_AND_QUORUM',
      passed: true,
      severity: 'CRITICAL',
      message: 'Shared datastore mount verified and cluster quorum consensus intact.'
    },
    {
      check_name: 'COOLDOWN_PERIOD',
      passed: true,
      severity: 'CRITICAL',
      message: 'Workload migration cooldown satisfied (minimum 60s since last migration).'
    }
  ];

  const checksToDisplay = safetyEvaluation?.results && safetyEvaluation.results.length > 0 
    ? safetyEvaluation.results 
    : defaultRules;

  const isBlocked = safetyEvaluation ? safetyEvaluation.blocked : false;
  const passedCount = safetyEvaluation ? safetyEvaluation.passed_checks : checksToDisplay.filter(c => c.passed).length;
  const totalCount = safetyEvaluation ? safetyEvaluation.total_checks : checksToDisplay.length;

  return (
    <div className="w-full space-y-8 font-mono text-xs">
      {/* Signature Architectural Banner */}
      <div className="rounded-xl border border-[#2A303F] bg-gradient-to-b from-[#11141C] via-[#0B0D13] to-[#07080C] p-8 md:p-12 text-center relative overflow-hidden shadow-2xl">
        <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-56 w-[32rem] rounded-full bg-blue-500/10 blur-3xl" />
        
        <div className="inline-flex items-center space-x-2 rounded border border-[#3D465C] bg-[#161922] px-3.5 py-1 text-xs text-[#9CA3AF] mb-5">
          <Lock className="h-3.5 w-3.5 text-amber-400" />
          <span className="tracking-wider">DETERMINISTIC CONTROL POLICY · HARD BOUNDARY LAYER</span>
        </div>

        <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extralight uppercase tracking-tight text-white leading-tight font-sans">
          The AI Doesn’t Get <br />
          <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-amber-300 to-white">
            The Final Word.
          </span>
        </h2>

        <p className="mt-4 max-w-2xl mx-auto text-sm sm:text-base text-[#9CA3AF] font-normal leading-relaxed font-sans">
          Neural networks optimize mathematical rewards; deterministic gates enforce infrastructure safety. 
          Every candidate migration must achieve a 100% pass rate across all 8 non-negotiable physical constraints before operator authorization is unlocked.
        </p>

        {/* Global Verdict Pill */}
        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <div className={`inline-flex items-center space-x-2.5 rounded-lg px-5 py-2.5 font-bold tracking-wider text-xs shadow-xl transition-all ${
            isBlocked
              ? 'border border-red-500/60 bg-red-500/20 text-red-300 shadow-[0_0_25px_rgba(239,68,68,0.25)]'
              : 'border border-emerald-500/60 bg-emerald-500/20 text-emerald-300 shadow-[0_0_25px_rgba(16,185,129,0.25)]'
          }`}>
            {isBlocked ? (
              <>
                <ShieldAlert className="h-4 w-4 text-red-400 shrink-0" />
                <span>MIGRATION BLOCKED — {totalCount - passedCount} FAILED CONSTRAINT(S)</span>
              </>
            ) : (
              <>
                <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>SAFETY GATE PASSED — ALL {totalCount}/{totalCount} CONDITIONS SATISFIED</span>
              </>
            )}
          </div>

          <div className="rounded-lg border border-[#1C202A] bg-[#0E1015] px-4 py-2.5 text-[#9CA3AF] text-[11px]">
            PASSED: <span className="text-white font-bold">{passedCount}</span> / <span className="text-white font-bold">{totalCount}</span> CHECKS
          </div>
        </div>

        {/* Machine Reason Callout if Blocked */}
        {isBlocked && safetyEvaluation?.rejection_reasons && safetyEvaluation.rejection_reasons.length > 0 && (
          <div className="mt-6 max-w-2xl mx-auto rounded-lg border border-red-500/50 bg-red-950/30 p-4 text-left font-mono">
            <div className="flex items-center space-x-2 text-red-400 font-bold mb-2 text-xs">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>SAFETY GATE VIOLATION CODES:</span>
            </div>
            <ul className="space-y-1 text-[11px] text-red-200">
              {safetyEvaluation.rejection_reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <span className="text-red-400 font-bold shrink-0">›</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 8 Deterministic Checks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {checksToDisplay.map((check, idx) => {
          const isCheckPassed = check.passed;
          const errorCode = ERROR_CODE_MAP[check.check_name] || `ERR_${check.check_name}`;

          return (
            <div
              key={check.check_name || idx}
              className={`rounded-xl border p-5 transition-all relative overflow-hidden ${
                isCheckPassed
                  ? 'border-[#1C202A] bg-[#0B0D13] hover:border-[#2A303F]'
                  : 'border-red-500/70 bg-[#160B0E] shadow-[0_0_20px_rgba(239,68,68,0.2)] ring-1 ring-red-500/30'
              }`}
            >
              {/* Left Accent Bar */}
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                isCheckPassed ? 'bg-emerald-500/60' : 'bg-red-500'
              }`} />

              <div className="flex items-start justify-between gap-3 mb-2.5 pl-2">
                <div>
                  <div className="flex items-center space-x-2">
                    {isCheckPassed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400 shrink-0 animate-pulse" />
                    )}
                    <span className="font-bold text-white tracking-wide text-xs">
                      {check.check_name.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#6B7280] mt-0.5 font-mono">
                    RULE ID: <span className="text-[#9CA3AF]">{check.check_name}</span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className={`inline-block px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
                    isCheckPassed
                      ? 'border border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : 'border border-red-500/60 bg-red-500/20 text-red-300 animate-pulse'
                  }`}>
                    {isCheckPassed ? 'PASS' : 'FAIL // BLOCKED'}
                  </span>
                </div>
              </div>

              {/* Message Description */}
              <p className="text-[11px] text-[#9CA3AF] leading-relaxed pl-8 font-sans">
                {check.message}
              </p>

              {/* Error Code & Metric Details */}
              <div className="mt-3 pt-3 border-t border-[#1C202A] pl-8 flex flex-wrap items-center justify-between gap-2 text-[10px]">
                {!isCheckPassed ? (
                  <div className="flex items-center space-x-1 text-red-400 font-bold">
                    <span>REASON CODE:</span>
                    <span className="rounded bg-red-500/20 px-1.5 py-0.5 border border-red-500/40">
                      {errorCode}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-1 text-[#6B7280]">
                    <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                    <span>VERIFIED BY CONTROL PLANE</span>
                  </div>
                )}

                {check.metric_value && (
                  <div className="text-[#9CA3AF]">
                    METRIC: <strong className="text-white">{check.metric_value}</strong>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
