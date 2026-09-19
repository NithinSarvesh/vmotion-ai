import React from 'react';
import { ShieldCheck, Layers } from 'lucide-react';
import type { ClusterState } from '../types';

interface HeaderProps {
  cluster: ClusterState | null;
  wsConnected: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  cluster,
  activeTab,
  setActiveTab,
  onOpenSettings
}) => {
  const isSim = !cluster || cluster.provider_name === 'simulation';
  const isDisconnected = cluster && cluster.is_live && !cluster.connected;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#1C202A] bg-[#08090C]/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Brand Identity */}
        <div className="flex items-center space-x-6">
          <div 
            onClick={() => setActiveTab('overview')}
            className="flex cursor-pointer items-center space-x-3 group"
          >
            <div className="relative flex h-8 w-8 items-center justify-center rounded border border-[#2A303F] bg-[#111319] group-hover:border-[#3D465C] transition-colors">
              <div className="h-2.5 w-2.5 rounded-full bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.8)]" />
              <div className="absolute inset-0 rounded animate-ping bg-blue-500/10" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-sm font-semibold tracking-wider text-white">
                VMOTION<span className="text-blue-400">.AI</span>
              </span>
              <span className="text-[10px] font-mono tracking-widest text-[#6B7280]">
                HYPERVISOR CONTROL PLANE
              </span>
            </div>
          </div>

          {/* Operational Mode Badge */}
          <div className="hidden sm:flex items-center space-x-2">
            {isDisconnected ? (
              <div className="flex items-center space-x-1.5 rounded border border-red-500/40 bg-red-500/10 px-2.5 py-1 text-[11px] font-mono text-red-400 animate-pulse">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                <span>LIVE CLUSTER DISCONNECTED</span>
              </div>
            ) : isSim ? (
              <div className="flex items-center space-x-1.5 rounded border border-[#2A303F] bg-[#111319] px-2.5 py-1 text-[11px] font-mono text-[#9CA3AF]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>SIMULATION MODE</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1.5 rounded border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-mono text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>LIVE: {cluster?.provider_name.toUpperCase()}</span>
              </div>
            )}
          </div>
        </div>

        {/* Center: Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1 font-mono text-xs">
          {[
            { id: 'overview', label: '01 OVERVIEW' },
            { id: 'topology', label: '02 TOPOLOGY' },
            { id: 'ai-engine', label: '03 AI & SAFETY' },
            { id: 'migrations', label: '04 MIGRATIONS' },
            { id: 'audit', label: '05 AUDIT' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded px-3 py-1.5 transition-colors ${
                activeTab === tab.id
                  ? 'border border-[#3D465C] bg-[#161922] text-white shadow-sm'
                  : 'text-[#9CA3AF] hover:bg-[#111319] hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Right: Governance Pill & Settings */}
        <div className="flex items-center space-x-3">
          <div className="hidden lg:flex items-center space-x-1.5 rounded border border-amber-500/30 bg-amber-500/5 px-2.5 py-1 text-[11px] font-mono text-amber-300">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
            <span>HUMAN APPROVAL REQUIRED</span>
          </div>

          <button
            onClick={onOpenSettings}
            className="flex items-center space-x-1.5 rounded border border-[#2A303F] bg-[#111319] px-3 py-1.5 font-mono text-xs text-[#9CA3AF] hover:border-[#3D465C] hover:text-white transition-colors"
          >
            <Layers className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">PROVIDER CONFIG</span>
          </button>
        </div>
      </div>
    </header>
  );
};
