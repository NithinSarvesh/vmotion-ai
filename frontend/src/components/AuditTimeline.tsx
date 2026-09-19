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
  Terminal,
  UserCheck
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

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'AI_RECOMMENDATION_GENERATED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-100 text-purple-700 border border-purple-200">
            <Brain className="h-3.5 w-3.5" />
          </div>
        );
      case 'SAFETY_CHECKS_EVALUATED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 border border-blue-200">
            <ShieldCheck className="h-3.5 w-3.5" />
          </div>
        );
      case 'SAFETY_CHECKS_BLOCKED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-700 border border-red-200">
            <ShieldAlert className="h-3.5 w-3.5" />
          </div>
        );
      case 'HUMAN_APPROVAL_GRANTED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
            <UserCheck className="h-3.5 w-3.5" />
          </div>
        );
      case 'HUMAN_APPROVAL_REJECTED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-amber-700 border border-amber-200">
            <ShieldAlert className="h-3.5 w-3.5" />
          </div>
        );
      case 'MIGRATION_TASK_STARTED':
      case 'MIGRATION_DISPATCHED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 border border-blue-200">
            <Zap className="h-3.5 w-3.5" />
          </div>
        );
      case 'DESTINATION_PLACEMENT_VERIFIED':
      case 'MIGRATION_VERIFIED':
      case 'VM_HEALTH_VERIFIED':
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" />
          </div>
        );
      default:
        return (
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-slate-700 border border-slate-200">
            <FileText className="h-3.5 w-3.5" />
          </div>
        );
    }
  };

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      if (filterType !== 'ALL') {
        const cat = getEventCategory(entry.event_type);
        if (cat !== filterType) return false;
      }

      if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase();
        const matchesType = entry.event_type.toLowerCase().includes(query);
        const matchesMsg = entry.message.toLowerCase().includes(query);
        const matchesVm = entry.vm_id?.toLowerCase().includes(query);
        if (!matchesType && !matchesMsg && !matchesVm) return false;
      }

      return true;
    });
  }, [entries, filterType, searchQuery]);

  return (
    <div className="w-full space-y-8 font-mono text-xs">
      {/* Header */}
      <div className="border-b border-[#E2E8F0] pb-6">
        <div className="flex items-center space-x-2 text-indigo-600 text-xs mb-1 font-bold tracking-wider">
          <Terminal className="h-4 w-4" />
          <span className="uppercase">06 // FORENSIC TIMELINE & AUDIT STREAM</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-light text-[#0F172A] uppercase tracking-tight font-sans">
          Append-Only Forensic Ledger
        </h2>
        <p className="text-sm text-[#475569] max-w-3xl mt-1 font-normal font-sans">
          Every telemetry observation, AI policy proposal, safety evaluation, human approval decision, 
          hypervisor command dispatch, and post-placement verification check is permanently recorded in an append-only ledger.
        </p>
      </div>

      {/* Control Bar: Category Filters & Search */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Category Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
            {(['ALL', 'AI', 'SAFETY', 'OPERATOR', 'MIGRATION', 'VERIFICATION'] as EventFilterType[]).map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  filterType === type
                    ? 'bg-[#0F172A] text-white font-bold shadow-2xs'
                    : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#94A3B8]" />
            <input
              type="text"
              placeholder="Search audit records..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-[#CBD5E1] bg-[#F8FAFC] pl-8 pr-3 py-1.5 text-xs text-[#0F172A] placeholder-[#94A3B8] focus:border-blue-500 focus:bg-white focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Event Timeline Stream */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xs">
        {filteredEntries.length === 0 ? (
          <div className="p-8 text-center text-[#94A3B8] font-sans text-xs">
            No audit records matched the active filter or search query.
          </div>
        ) : (
          <div className="space-y-4">
            {filteredEntries.map((entry) => {
              const isExpanded = expandedId === entry.id;
              const dateStr = new Date(entry.timestamp * 1000).toLocaleTimeString();
              const fullDateStr = new Date(entry.timestamp * 1000).toISOString();

              return (
                <div
                  key={entry.id}
                  className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 transition-all hover:bg-white hover:border-[#CBD5E1]"
                >
                  <div 
                    onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer"
                  >
                    <div className="flex items-start space-x-3.5">
                      <div className="pt-0.5">{getEventBadge(entry.event_type)}</div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-[#0F172A] text-xs">{entry.event_type}</span>
                          {entry.vm_id && (
                            <span className="rounded bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.2 text-[10px] font-bold">
                              {entry.vm_id}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-[#475569] mt-1 font-sans">
                          {entry.message}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 text-[#64748B] text-[11px] shrink-0 sm:text-right">
                      <span>{dateStr}</span>
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>

                  {/* Expandable Technical Forensic Payload */}
                  {isExpanded && (
                    <div className="mt-4 pt-3 border-t border-[#E2E8F0] text-[11px] space-y-3">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
                        <div>
                          <span className="text-[#94A3B8] block">EVENT ID:</span>
                          <span className="text-[#0F172A] font-bold">{entry.id}</span>
                        </div>
                        <div>
                          <span className="text-[#94A3B8] block">TIMESTAMP (UTC):</span>
                          <span className="text-[#0F172A]">{fullDateStr}</span>
                        </div>
                        <div>
                          <span className="text-[#94A3B8] block">TARGET NODE:</span>
                          <span className="text-[#0F172A]">{entry.target_node || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-[#94A3B8] block">TASK UPID:</span>
                          <span className="text-[#0F172A]">{entry.task_id || 'N/A'}</span>
                        </div>
                      </div>

                      {entry.details && Object.keys(entry.details).length > 0 && (
                        <div>
                          <span className="text-[#94A3B8] text-[10px] block mb-1 uppercase font-bold">FORENSIC JSON METRIC PAYLOAD:</span>
                          <pre className="rounded-lg border border-[#CBD5E1] bg-white p-3 text-[10px] text-[#0F172A] overflow-x-auto">
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
