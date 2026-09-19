import React, { useState, useMemo } from 'react';
import { 
  FileText, 
  ChevronDown, 
  ChevronUp, 
  Search, 
  CheckCircle2, 
  ShieldCheck, 
  ShieldAlert, 
  Brain, 
  Zap, 
  Terminal 
} from 'lucide-react';
import type { AuditEntry } from '../types';

interface AuditTimelineProps {
  entries: AuditEntry[];
}

type EventFilterType = 'ALL' | 'AI' | 'SAFETY' | 'OPERATOR' | 'MIGRATION' | 'VERIFICATION';

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ entries }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<EventFilterType>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const getEventCategory = (eventType: string): EventFilterType => {
    if (eventType.startsWith('AI_')) return 'AI';
    if (eventType.startsWith('SAFETY_')) return 'SAFETY';
    if (eventType.startsWith('HUMAN_') || eventType.startsWith('OPERATOR_')) return 'OPERATOR';
    if (eventType.startsWith('MIGRATION_TASK_') || eventType.includes('DISPATCH')) return 'MIGRATION';
    if (eventType.includes('VERIF')) return 'VERIFICATION';
    return 'ALL';
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'AI_RECOMMENDATION_GENERATED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
            <Brain className="h-3 w-3" />
          </div>
        );
      case 'SAFETY_CHECKS_EVALUATED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <ShieldCheck className="h-3 w-3" />
          </div>
        );
      case 'SAFETY_CHECKS_BLOCKED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
            <ShieldAlert className="h-3 w-3" />
          </div>
        );
      case 'HUMAN_APPROVAL_GRANTED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" />
          </div>
        );
      case 'HUMAN_APPROVAL_REJECTED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <ShieldAlert className="h-3 w-3" />
          </div>
        );
      case 'MIGRATION_TASK_STARTED':
      case 'MIGRATION_DISPATCHED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse">
            <Zap className="h-3 w-3" />
          </div>
        );
      case 'DESTINATION_PLACEMENT_VERIFIED':
      case 'MIGRATION_VERIFIED':
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.8)]">
            <CheckCircle2 className="h-3 w-3" />
          </div>
        );
      default:
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
            <FileText className="h-3 w-3" />
          </div>
        );
    }
  };

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      // Category filter
      if (filterType !== 'ALL') {
        const cat = getEventCategory(entry.event_type);
        if (cat !== filterType) return false;
      }

      // Text search
      if (searchQuery.trim() !== '') {
        const q = searchQuery.toLowerCase();
        const matchType = entry.event_type.toLowerCase().includes(q);
        const matchMsg = entry.message.toLowerCase().includes(q);
        const matchDetails = entry.details ? JSON.stringify(entry.details).toLowerCase().includes(q) : false;
        if (!matchType && !matchMsg && !matchDetails) return false;
      }

      return true;
    });
  }, [entries, filterType, searchQuery]);

  return (
    <div className="w-full space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="border-b border-[#1C202A] pb-5">
        <div className="flex items-center space-x-2 text-blue-400 text-xs mb-1">
          <FileText className="h-4 w-4" />
          <span className="tracking-widest uppercase">05 // IMMUTABLE AUDIT TRAIL & FORENSIC LEDGER</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-light text-white uppercase tracking-tight font-sans">
          Append-Only Audit Ledger & Governance Stream
        </h2>
        <p className="text-sm text-[#9CA3AF] max-w-3xl mt-1 font-normal font-sans">
          Every telemetry tick, neural recommendation, deterministic safety check, human approval signature, 
          and post-migration hypervisor assertion is logged into an append-only immutable audit ledger.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-[#1C202A] bg-[#0A0D14] p-3">
        {/* Category Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[#6B7280] text-[10px] uppercase mr-1">FILTER:</span>
          {(['ALL', 'AI', 'SAFETY', 'OPERATOR', 'MIGRATION', 'VERIFICATION'] as EventFilterType[]).map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`rounded px-2.5 py-1 text-[10px] font-bold uppercase transition-all cursor-pointer ${
                filterType === type
                  ? 'border border-blue-500/50 bg-blue-500/20 text-blue-300'
                  : 'text-[#6B7280] hover:text-[#9CA3AF] hover:bg-[#14171E]'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Search Box */}
        <div className="relative flex items-center">
          <Search className="absolute left-2.5 h-3.5 w-3.5 text-[#6B7280]" />
          <input
            type="text"
            placeholder="Search events, VMs, nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-64 rounded-lg border border-[#1C202A] bg-[#0E1119] pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#4B5563] focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Timeline Stream Container */}
      <div className="rounded-xl border border-[#1C202A] bg-[#0A0D14] p-6 shadow-2xl">
        <div className="relative pl-8 space-y-4 before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-px before:bg-[#1C202A]">
          {filteredEntries.map((entry) => {
            const isExpanded = expandedId === entry.id;
            const dateObj = entry.timestamp ? new Date(entry.timestamp * 1000) : new Date();
            const timeLocal = dateObj.toLocaleTimeString('en-US', { hour12: false });
            const timeISO = dateObj.toISOString();

            return (
              <div key={entry.id} className="relative group">
                {/* Event Node Icon */}
                <div className="absolute -left-8 top-1.5 flex items-center justify-center">
                  {getEventIcon(entry.event_type)}
                </div>

                {/* Event Card */}
                <div 
                  onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  className={`rounded-lg border transition-all cursor-pointer p-3.5 ${
                    isExpanded
                      ? 'border-blue-500/50 bg-[#121622] shadow-md'
                      : 'border-[#1C202A] bg-[#0E1119] hover:border-[#2A3144] hover:bg-[#111420]'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-3">
                      <span className="text-blue-400 font-bold tracking-tight">{timeLocal}</span>
                      <span className="text-white font-medium text-xs">{entry.message}</span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <span className="text-[10px] font-bold uppercase bg-[#07090E] px-2 py-0.5 rounded border border-[#1C202A] text-[#9CA3AF]">
                        {entry.event_type}
                      </span>
                      {isExpanded ? <ChevronUp className="h-3.5 w-3.5 text-[#9CA3AF]" /> : <ChevronDown className="h-3.5 w-3.5 text-[#6B7280]" />}
                    </div>
                  </div>

                  {/* Expanded Structured Forensic Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-3 border-t border-[#1C202A] space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-[#6B7280]">
                        <span>EVENT ID: <strong className="text-white">{entry.id}</strong></span>
                        <span>UTC TIMESTAMP: <strong className="text-white">{timeISO}</strong></span>
                      </div>

                      {entry.details && Object.keys(entry.details).length > 0 ? (
                        <div className="rounded-lg border border-[#1C202A] bg-[#06070B] p-3">
                          <div className="flex items-center space-x-1.5 text-[10px] text-[#6B7280] mb-2">
                            <Terminal className="h-3 w-3 text-blue-400" />
                            <span className="uppercase font-bold">RAW EVENT TELEMETRY PAYLOAD</span>
                          </div>
                          <pre className="text-[11px] text-[#9CA3AF] overflow-x-auto leading-relaxed font-mono">
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </div>
                      ) : (
                        <div className="text-[10px] text-[#6B7280] italic">
                          No supplemental payload fields attached to this event.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {filteredEntries.length === 0 && (
            <div className="py-8 text-center text-[#6B7280] font-mono">
              {entries.length === 0 
                ? 'No audit entries recorded in current session.' 
                : 'No audit events matched the current category or search query.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
