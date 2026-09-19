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
  const [activeSection, setActiveSection] = useState<string>('overview');
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

    const rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
    };
  }, []);

  // Scroll spy to keep activeSection in sync with scroll position
  useEffect(() => {
    const sectionIds = ['overview', 'topology', 'ai-engine', 'safety', 'migrations', 'audit'];
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 220;
      for (let i = sectionIds.length - 1; i >= 0; i--) {
        const id = sectionIds[i];
        const el = document.getElementById(`section-${id}`);
        if (el && scrollPosition >= el.offsetTop) {
          setActiveSection(id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNavigateSection = (sectionId: string) => {
    setActiveSection(sectionId);
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const pendingProposal = proposals.find(p => p.status === 'PENDING_APPROVAL') || null;

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#0F172A] selection:bg-blue-600 selection:text-white technical-grid-light relative">
      {/* Top Header */}
      <Header
        cluster={cluster}
        wsConnected={wsConnected}
        activeSection={activeSection}
        onNavigateSection={handleNavigateSection}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Content Sections - Single Scroll Narrative */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-24 pb-32 pt-4">
        {/* Section 01: Hero & Spatial Cluster Overview */}
        <section id="section-overview" className="scroll-mt-20">
          <HeroSection
            cluster={cluster}
            telemetry={telemetry}
            recommendation={recommendation}
            proposals={proposals}
            onNavigateSection={handleNavigateSection}
            onTriggerAi={actions.refresh}
          />
        </section>

        {/* Section 02: Compute Fabric & Interconnect Topology */}
        <section id="section-topology" className="scroll-mt-20 pt-6">
          <TopologyCanvas
            cluster={cluster}
            telemetry={telemetry}
            activeTasks={activeTasks}
            recommendation={recommendation}
          />
        </section>

        {/* Section 03: PPO V5 AI Decision Engine */}
        <section id="section-ai-engine" className="scroll-mt-20 pt-6">
          <AiDecisionSection
            recommendation={recommendation}
            safetyEvaluation={safetyEvaluation}
            modelHealth={modelHealth}
            proposals={proposals}
            onApprove={actions.approveProposal}
            onReject={actions.rejectProposal}
          />
        </section>

        {/* Section 04: Deterministic Safety Gate & Operator Signoff */}
        <section id="section-safety" className="scroll-mt-20 pt-6">
          <SafetyGateSection
            safetyEvaluation={safetyEvaluation}
            activeProposal={pendingProposal}
            onApprove={actions.approveProposal}
            onReject={actions.rejectProposal}
          />
        </section>

        {/* Section 05: Migration Orchestration FSM & Placement Health */}
        <section id="section-migrations" className="scroll-mt-20 pt-6">
          <MigrationCenter
            activeTasks={activeTasks}
            completedTasks={completedTasks}
          />
        </section>

        {/* Section 06: Append-Only Forensic Audit Ledger */}
        <section id="section-audit" className="scroll-mt-20 pt-6">
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

      {/* Architectural Light Footer */}
      <footer className="border-t border-[#E2E8F0] bg-white py-12 text-center font-mono text-xs text-[#64748B] shadow-2xs">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center space-y-1 sm:space-y-0 sm:space-x-3 text-left">
            <span className="font-bold tracking-wider text-[#0F172A]">VMOTION AI</span>
            <span className="hidden sm:inline text-[#CBD5E1]">•</span>
            <span className="text-[#475569]">HYPERVISOR LIVE MIGRATION CONTROL PLANE</span>
            <span className="hidden sm:inline text-[#CBD5E1]">•</span>
            <span className="text-[11px] text-[#94A3B8]">PROD-READY ARCHITECTURE</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px]">
            <span className="inline-flex items-center space-x-1.5 rounded bg-[#F1F5F9] px-2 py-0.5 border border-[#E2E8F0]">
              <span className="text-[#64748B]">POLICY:</span>
              <span className="font-semibold text-[#0F172A]">PPO V5 (103 FEATURES)</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 rounded bg-[#F1F5F9] px-2 py-0.5 border border-[#E2E8F0]">
              <span className="text-[#64748B]">SAFETY:</span>
              <span className="font-semibold text-emerald-700">DETERMINISTIC 8-RULE GATE</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 rounded bg-[#F1F5F9] px-2 py-0.5 border border-[#E2E8F0]">
              <span className="text-[#64748B]">GOVERNANCE:</span>
              <span className="font-semibold text-blue-700">HUMAN-IN-THE-LOOP</span>
            </span>
          </div>
        </div>

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-6 pt-6 border-t border-[#F1F5F9] flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#94A3B8]">
          <p>STRICT ISOLATION PROTOCOL ACTIVE. SIMULATION RUNS ON SYNTHETIC TELEMETRY. NO UNVERIFIED HARDWARE ACTIONS.</p>
          <p className="mt-2 sm:mt-0">SPECIFICATION v1.0.0 • FASTAPI &amp; REACT 19</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
