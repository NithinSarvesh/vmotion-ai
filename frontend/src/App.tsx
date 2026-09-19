import { useState, useEffect } from 'react';
import Lenis from 'lenis';
import { useWebSocketTelemetry } from './hooks/useWebSocketTelemetry';
import { Header } from './components/Header';
import { HeroSection } from './components/HeroSection';
import { TopologyCanvas } from './components/TopologyCanvas';
import { AiDecisionSection } from './components/AiDecisionSection';
import { SafetyGateSection } from './components/SafetyGateSection';
import { MigrationCenter } from './components/MigrationCenter';
import { AuditTimeline } from './components/AuditTimeline';
import { ModeSettingsModal } from './components/ModeSettingsModal';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  const {
    cluster,
    telemetry,
    modelHealth,
    recommendation,
    safetyEvaluation,
    proposals,
    activeTasks,
    completedTasks,
    auditEntries,
    wsConnected,
    actions
  } = useWebSocketTelemetry();

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
    });

    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);

    return () => {
      lenis.destroy();
    };
  }, []);

  const handleNavigateTab = (tab: string) => {
    setActiveTab(tab);
    const element = document.getElementById(`section-${tab}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#08090C] text-[#F3F4F6] selection:bg-blue-500 selection:text-white">
      {/* Top Header */}
      <Header
        cluster={cluster}
        wsConnected={wsConnected}
        activeTab={activeTab}
        setActiveTab={handleNavigateTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Content Sections */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-16 pb-24">
        {/* Section 01: Hero & Overview */}
        <section id="section-overview">
          <HeroSection
            cluster={cluster}
            telemetry={telemetry}
            recommendation={recommendation}
            proposals={proposals}
            onNavigateTab={handleNavigateTab}
            onTriggerAi={actions.refresh}
          />
        </section>

        {/* Section 02: Topology & Interconnect */}
        <section id="section-topology" className="pt-8">
          <TopologyCanvas
            cluster={cluster}
            telemetry={telemetry}
            activeTasks={activeTasks}
            recommendation={recommendation}
          />
        </section>

        {/* Section 03: AI Engine & Rationale */}
        <section id="section-ai-engine" className="pt-8">
          <AiDecisionSection
            recommendation={recommendation}
            safetyEvaluation={safetyEvaluation}
            modelHealth={modelHealth}
            proposals={proposals}
            onApprove={actions.approveProposal}
            onReject={actions.rejectProposal}
          />
        </section>

        {/* Section 04: Deterministic Safety Gate */}
        <section id="section-safety" className="pt-8">
          <SafetyGateSection
            safetyEvaluation={safetyEvaluation}
          />
        </section>

        {/* Section 05: Migration Lifecycle & Verification */}
        <section id="section-migrations" className="pt-8">
          <MigrationCenter
            activeTasks={activeTasks}
            completedTasks={completedTasks}
          />
        </section>

        {/* Section 06: Immutable Audit Ledger */}
        <section id="section-audit" className="pt-8">
          <AuditTimeline
            entries={auditEntries}
          />
        </section>
      </main>

      {/* Provider Switcher Modal */}
      <ModeSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        cluster={cluster}
        onSwitchProvider={actions.switchProviderMode}
      />

      {/* Footer */}
      <footer className="border-t border-[#1C202A] bg-[#050608] py-8 text-center font-mono text-xs text-[#6B7280]">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-white font-semibold">VMOTION AI</span>
            <span>—</span>
            <span>HYPERVISOR LIVE MIGRATION CONTROL PLANE</span>
          </div>

          <div className="flex items-center space-x-4 text-[11px]">
            <span>ENGINE: FASTAPI + PYTHON 3.11</span>
            <span className="text-[#3D465C]">|</span>
            <span>RL POLICY: MASKABLE_PPO (103 FEATURES)</span>
            <span className="text-[#3D465C]">|</span>
            <span className="text-emerald-400">SAFETY: DETERMINISTIC GATE</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
