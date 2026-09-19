import React, { useEffect, useState } from 'react';
import { ShieldCheck, Layers } from 'lucide-react';
import type { ClusterState } from '../types';

interface HeaderProps {
  cluster: ClusterState | null;
  wsConnected: boolean;
  activeSection: string;
  onNavigateSection: (sectionId: string) => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  cluster,
  wsConnected,
  activeSection,
  onNavigateSection,
  onOpenSettings
}) => {
  const [scrollProgress, setScrollProgress] = useState(0);

  const isSim = !cluster || cluster.provider_name === 'simulation';
  const isDisconnected = cluster && cluster.is_live && !cluster.connected;

  useEffect(() => {
    const handleScroll = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (totalHeight > 0) {
        const current = window.scrollY;
        setScrollProgress(Math.min(100, Math.max(0, (current / totalHeight) * 100)));
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { id: 'overview', label: '01 INTRO' },
    { id: 'topology', label: '02 FABRIC' },
    { id: 'ai-engine', label: '03 AI ENGINE' },
    { id: 'safety', label: '04 SAFETY' },
    { id: 'migrations', label: '05 MIGRATIONS' },
    { id: 'audit', label: '06 AUDIT' }
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#E2E8F0] bg-white/90 backdrop-blur-md transition-all">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Left: Brand & Environment Indicator */}
        <div className="flex items-center space-x-5">
          <button 
            onClick={() => onNavigateSection('overview')}
            className="flex cursor-pointer items-center space-x-2.5 text-left group"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#CBD5E1] bg-[#F8FAFC] group-hover:border-[#94A3B8] transition-colors shadow-sm">
              <div className="h-2 w-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(37,99,235,0.6)]" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-sm font-bold tracking-tight text-[#0F172A]">
                VMOTION<span className="text-blue-600">.AI</span>
              </span>
              <span className="text-[9px] font-mono tracking-widest text-[#64748B]">
                CONTROL PLANE
              </span>
            </div>
          </button>

          <div className="h-5 w-px bg-[#E2E8F0] hidden sm:block" />

          {/* Persistent Environment Mode Pill */}
          <div className="hidden sm:flex items-center">
            {!wsConnected ? (
              <div className="flex items-center space-x-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-mono text-[11px] text-amber-800 shadow-xs">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="font-semibold">CONNECTING TO TELEMETRY</span>
              </div>
            ) : isDisconnected ? (
              <div className="flex items-center space-x-2 rounded-full border border-red-200 bg-red-50 px-3 py-1 font-mono text-[11px] text-red-700 shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-600" />
                </span>
                <span className="font-semibold">LIVE / PROXMOX · DISCONNECTED</span>
              </div>
            ) : isSim ? (
              <div className="flex items-center space-x-2 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1 font-mono text-[11px] text-[#475569] shadow-xs">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span>SIMULATION <span className="text-[#94A3B8]">· SYNTHETIC CLUSTER</span></span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 font-mono text-[11px] text-emerald-800 shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
                </span>
                <span className="font-semibold">LIVE / {cluster?.provider_name.toUpperCase()} · CONNECTED</span>
              </div>
            )}
          </div>
        </div>

        {/* Center: Scroll Navigation Anchor Links */}
        <nav className="hidden md:flex items-center space-x-1 font-mono text-xs">
          {navItems.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigateSection(item.id)}
                className={`rounded-md px-3 py-1.5 transition-all cursor-pointer ${
                  isActive
                    ? 'border border-[#CBD5E1] bg-[#F1F5F9] text-[#0F172A] font-semibold shadow-xs'
                    : 'text-[#64748B] hover:text-[#0F172A] hover:bg-[#F8FAFC]'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Right: Governance Pill & Environment Switcher */}
        <div className="flex items-center space-x-3">
          <div className="hidden lg:flex items-center space-x-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-mono text-[11px] text-amber-800 shadow-xs">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-600" />
            <span className="font-medium">HUMAN APPROVAL REQUIRED</span>
          </div>

          <button
            onClick={onOpenSettings}
            className="flex items-center space-x-1.5 rounded-lg border border-[#CBD5E1] bg-white px-3.5 py-1.5 font-mono text-xs font-semibold text-[#0F172A] hover:border-[#94A3B8] hover:bg-[#F8FAFC] transition-colors shadow-xs cursor-pointer"
          >
            <Layers className="h-3.5 w-3.5 text-blue-600" />
            <span>INFRASTRUCTURE</span>
          </button>
        </div>
      </div>

      {/* Micro Scroll Progress Bar */}
      <div className="w-full h-[2px] bg-[#E2E8F0]">
        <div 
          className="h-full bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 transition-all duration-75"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>
    </header>
  );
};
