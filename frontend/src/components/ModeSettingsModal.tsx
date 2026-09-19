import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  AlertTriangle,
  Check,
  Activity,
  Server,
  ShieldCheck,
  RefreshCw,
  Clock,
  Cpu
} from 'lucide-react';
import type { ClusterState, ProviderConnectionResult, ClusterConfig } from '../types';

interface ModeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  cluster: ClusterState | null;
  onSwitchProvider: (provider: 'simulation' | 'proxmox' | 'libvirt') => Promise<void>;
}

export const ModeSettingsModal: React.FC<ModeSettingsModalProps> = ({
  isOpen,
  onClose,
  cluster,
  onSwitchProvider
}) => {
  const [selectedProvider, setSelectedProvider] = useState<'simulation' | 'proxmox' | 'libvirt'>(
    (cluster?.provider_name as any) || 'simulation'
  );
  const [modalTab, setModalTab] = useState<'config' | 'matrix'>('config');
  const [loading, setLoading] = useState<boolean>(false);
  const [testingConnection, setTestingConnection] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<ProviderConnectionResult | null>(null);

  // Configuration form state
  const [proxmoxEndpoint, setProxmoxEndpoint] = useState<string>('https://192.168.1.100:8006/api2/json');
  const [proxmoxUser, setProxmoxUser] = useState<string>('root@pam');
  const [proxmoxTokenId, setProxmoxTokenId] = useState<string>('vmotion');
  const [proxmoxTokenSecret, setProxmoxTokenSecret] = useState<string>('');
  const [tokenConfiguredOnServer, setTokenConfiguredOnServer] = useState<boolean>(false);
  const [proxmoxVerifySsl, setProxmoxVerifySsl] = useState<boolean>(false);
  const [libvirtUri, setLibvirtUri] = useState<string>('qemu+ssh://root@192.168.1.100/system');

  // Load existing config on modal open
  useEffect(() => {
    if (!isOpen) {
      setTestResult(null);
      return;
    }

    fetch('/api/cluster/config')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: ClusterConfig | null) => {
        if (data) {
          if (data.provider_type) setSelectedProvider(data.provider_type);
          if (data.proxmox) {
            setProxmoxEndpoint(data.proxmox.endpoint || 'https://192.168.1.100:8006/api2/json');
            setProxmoxUser(data.proxmox.user || 'root@pam');
            setProxmoxTokenId(data.proxmox.token_id || 'vmotion');
            setTokenConfiguredOnServer(data.proxmox.token_secret_configured);
            setProxmoxVerifySsl(data.proxmox.verify_ssl ?? false);
          }
          if (data.libvirt) {
            setLibvirtUri(data.libvirt.uri || 'qemu+ssh://root@192.168.1.100/system');
          }
        }
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const payload: Record<string, any> = {
        provider_type: selectedProvider
      };

      if (selectedProvider === 'proxmox') {
        payload.proxmox_endpoint = proxmoxEndpoint;
        payload.proxmox_user = proxmoxUser;
        payload.proxmox_token_id = proxmoxTokenId;
        if (proxmoxTokenSecret.trim()) {
          payload.proxmox_token_secret = proxmoxTokenSecret.trim();
        }
        payload.proxmox_verify_ssl = proxmoxVerifySsl;
      } else if (selectedProvider === 'libvirt') {
        payload.libvirt_uri = libvirtUri;
      }

      const res = await fetch('/api/cluster/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to execute diagnostic`);
      }

      const data: ProviderConnectionResult = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({
        provider: selectedProvider,
        status: 'DISCONNECTED',
        node_count: 0,
        vm_count: 0,
        message: err.message || 'Diagnostic communication failure'
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveAndApply = async () => {
    setLoading(true);
    try {
      const configPayload: Record<string, any> = {
        provider_type: selectedProvider
      };

      if (selectedProvider === 'proxmox') {
        configPayload.proxmox_endpoint = proxmoxEndpoint;
        configPayload.proxmox_user = proxmoxUser;
        configPayload.proxmox_token_id = proxmoxTokenId;
        if (proxmoxTokenSecret.trim()) {
          configPayload.proxmox_token_secret = proxmoxTokenSecret.trim();
        }
        configPayload.proxmox_verify_ssl = proxmoxVerifySsl;
      } else if (selectedProvider === 'libvirt') {
        configPayload.libvirt_uri = libvirtUri;
      }

      // Save parameters
      const saveRes = await fetch('/api/cluster/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Operator-Key': 'vmotion-operator-key-default'
        },
        body: JSON.stringify(configPayload)
      });
      if (!saveRes.ok) {
        const errData = await saveRes.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${saveRes.status}`);
      }

      // Switch provider mode
      await onSwitchProvider(selectedProvider);
      setLoading(false);
      onClose();
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'CONNECTED':
        return (
          <span className="inline-flex items-center space-x-1.5 rounded bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>CONNECTED</span>
          </span>
        );
      case 'AUTHENTICATION_ERROR':
        return (
          <span className="inline-flex items-center space-x-1.5 rounded bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-400 border border-rose-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
            <span>AUTHENTICATION ERROR</span>
          </span>
        );
      case 'DISCONNECTED':
        return (
          <span className="inline-flex items-center space-x-1.5 rounded bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            <span>DISCONNECTED</span>
          </span>
        );
      case 'UNAVAILABLE':
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 rounded bg-[#2A303F] px-2.5 py-1 text-xs font-semibold text-slate-300 border border-[#3D465C]">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
            <span>UNAVAILABLE</span>
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 font-mono text-xs overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-lg border border-[#2A303F] bg-[#0E1015] p-6 shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1C202A] pb-4 mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="rounded p-1.5 bg-blue-500/10 border border-blue-500/30 text-blue-400">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Virtualization Infrastructure & Provider Manager
              </h3>
              <p className="text-[11px] text-[#6B7280]">
                Unified Provider Abstraction • Simulation & Live Hypervisors
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[#6B7280] hover:text-white hover:bg-[#14171E] cursor-pointer transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-[#1C202A] mb-5 font-mono text-xs">
          <button
            onClick={() => setModalTab('config')}
            className={`pb-2.5 px-4 font-semibold uppercase tracking-wider transition-colors cursor-pointer border-b-2 ${
              modalTab === 'config'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#6B7280] hover:text-[#9CA3AF]'
            }`}
          >
            PROVIDER CONFIGURATION
          </button>
          <button
            onClick={() => setModalTab('matrix')}
            className={`pb-2.5 px-4 font-semibold uppercase tracking-wider transition-colors cursor-pointer border-b-2 flex items-center space-x-1.5 ${
              modalTab === 'matrix'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-[#6B7280] hover:text-[#9CA3AF]'
            }`}
          >
            <span>VERIFICATION MATRIX</span>
            <span className="rounded bg-emerald-500/10 text-emerald-400 text-[10px] px-1.5 py-0.5 border border-emerald-500/30">
              ZERO FALSE CLAIMS
            </span>
          </button>
        </div>

        {modalTab === 'config' ? (
          <>
        {/* Provider Selector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
          {/* Card 1: Simulation */}
          <div
            onClick={() => {
              setSelectedProvider('simulation');
              setTestResult(null);
            }}
            className={`rounded-md border p-3.5 cursor-pointer transition-all ${
              selectedProvider === 'simulation'
                ? 'border-blue-500 bg-[#14171E] shadow-sm ring-1 ring-blue-500/30'
                : 'border-[#1C202A] bg-[#0A0C10] hover:border-[#2A303F]'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-white text-xs">SIMULATION</span>
              {selectedProvider === 'simulation' && <Check className="h-3.5 w-3.5 text-blue-400" />}
            </div>
            <p className="text-[10px] text-[#9CA3AF] leading-relaxed">
              In-memory cluster with 3 nodes, 6 workloads, load drift, and migration physics.
            </p>
          </div>

          {/* Card 2: Proxmox VE */}
          <div
            onClick={() => {
              setSelectedProvider('proxmox');
              setTestResult(null);
            }}
            className={`rounded-md border p-3.5 cursor-pointer transition-all ${
              selectedProvider === 'proxmox'
                ? 'border-blue-500 bg-[#14171E] shadow-sm ring-1 ring-blue-500/30'
                : 'border-[#1C202A] bg-[#0A0C10] hover:border-[#2A303F]'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-white text-xs">PROXMOX VE</span>
              {selectedProvider === 'proxmox' && <Check className="h-3.5 w-3.5 text-blue-400" />}
            </div>
            <p className="text-[10px] text-[#9CA3AF] leading-relaxed">
              Live Proxmox cluster via REST API v2 tokens. Real UPID tracking and migration.
            </p>
          </div>

          {/* Card 3: Libvirt / KVM */}
          <div
            onClick={() => {
              setSelectedProvider('libvirt');
              setTestResult(null);
            }}
            className={`rounded-md border p-3.5 cursor-pointer transition-all ${
              selectedProvider === 'libvirt'
                ? 'border-blue-500 bg-[#14171E] shadow-sm ring-1 ring-blue-500/30'
                : 'border-[#1C202A] bg-[#0A0C10] hover:border-[#2A303F]'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-white text-xs">LIBVIRT / KVM</span>
              {selectedProvider === 'libvirt' && <Check className="h-3.5 w-3.5 text-blue-400" />}
            </div>
            <p className="text-[10px] text-[#9CA3AF] leading-relaxed">
              Linux hypervisors via remote URI (<code className="text-blue-300">qemu+ssh://</code>).
            </p>
          </div>
        </div>

        {/* Dynamic Provider Configuration Section */}
        <div className="rounded-md border border-[#1C202A] bg-[#0A0C10] p-4 mb-5 space-y-3.5">
          <div className="flex items-center justify-between border-b border-[#1C202A] pb-2">
            <span className="text-[11px] font-bold text-slate-200 uppercase tracking-wide flex items-center space-x-1.5">
              <Server className="h-3.5 w-3.5 text-blue-400" />
              <span>
                {selectedProvider === 'simulation' && 'Simulation Provider Configuration'}
                {selectedProvider === 'proxmox' && 'Proxmox VE REST API Credentials'}
                {selectedProvider === 'libvirt' && 'Libvirt Connection URI'}
              </span>
            </span>
            <span className="text-[10px] text-[#6B7280]">
              {selectedProvider === 'simulation' ? 'Local Memory' : 'Physical Network'}
            </span>
          </div>

          {selectedProvider === 'simulation' && (
            <div className="text-[11px] text-[#9CA3AF] leading-relaxed space-y-2 py-1">
              <p>
                The Simulation Provider enables safe development, algorithmic benchmarking, and PPO agent training without requiring physical hypervisor hardware.
              </p>
              <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[10px]">
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block">COMPUTE NODES</span>
                  <span className="text-white font-semibold">3 (node-01, node-02, node-03)</span>
                </div>
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block">ACTIVE WORKLOADS</span>
                  <span className="text-white font-semibold">6 synthetic VMs (vm-101..106)</span>
                </div>
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block">LOAD DYNAMICS</span>
                  <span className="text-white font-semibold">Sinusoidal drift + dirty pages</span>
                </div>
              </div>
            </div>
          )}

          {selectedProvider === 'proxmox' && (
            <div className="space-y-3 text-[11px]">
              <div>
                <label className="block text-[#9CA3AF] mb-1 font-medium">API Endpoint URL</label>
                <input
                  type="text"
                  value={proxmoxEndpoint}
                  onChange={(e) => setProxmoxEndpoint(e.target.value)}
                  placeholder="https://192.168.1.100:8006/api2/json"
                  className="w-full rounded border border-[#2A303F] bg-[#14171E] px-3 py-1.5 text-white focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#9CA3AF] mb-1 font-medium">User Account</label>
                  <input
                    type="text"
                    value={proxmoxUser}
                    onChange={(e) => setProxmoxUser(e.target.value)}
                    placeholder="root@pam or vmotion-bot@pve"
                    className="w-full rounded border border-[#2A303F] bg-[#14171E] px-3 py-1.5 text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[#9CA3AF] mb-1 font-medium">API Token ID</label>
                  <input
                    type="text"
                    value={proxmoxTokenId}
                    onChange={(e) => setProxmoxTokenId(e.target.value)}
                    placeholder="vmotion"
                    className="w-full rounded border border-[#2A303F] bg-[#14171E] px-3 py-1.5 text-white focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#9CA3AF] mb-1 font-medium flex items-center justify-between">
                  <span>API Token Secret (UUID)</span>
                  {tokenConfiguredOnServer && (
                    <span className="text-[10px] text-emerald-400 font-normal">
                      ✓ Active token configured on server (leave blank to keep)
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={proxmoxTokenSecret}
                  onChange={(e) => setProxmoxTokenSecret(e.target.value)}
                  placeholder={
                    tokenConfiguredOnServer
                      ? '••••••••••••••••••••••••••••••••••••'
                      : 'Enter API token secret UUID (e.g. 550e8400-e29b-41d4-a716...)'
                  }
                  className="w-full rounded border border-[#2A303F] bg-[#14171E] px-3 py-1.5 text-white focus:border-blue-500 focus:outline-none placeholder:text-[#4B5563]"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="proxmox_verify_ssl"
                  checked={proxmoxVerifySsl}
                  onChange={(e) => setProxmoxVerifySsl(e.target.checked)}
                  className="rounded border-[#2A303F] bg-[#14171E] text-blue-500 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="proxmox_verify_ssl" className="text-[11px] text-[#9CA3AF] cursor-pointer">
                  Verify SSL Certificate (Disable if Proxmox uses default self-signed certificate)
                </label>
              </div>
            </div>
          )}

          {selectedProvider === 'libvirt' && (
            <div className="space-y-3 text-[11px]">
              <div>
                <label className="block text-[#9CA3AF] mb-1 font-medium">Libvirt Remote URI</label>
                <input
                  type="text"
                  value={libvirtUri}
                  onChange={(e) => setLibvirtUri(e.target.value)}
                  placeholder="qemu+ssh://root@192.168.1.100/system"
                  className="w-full rounded border border-[#2A303F] bg-[#14171E] px-3 py-1.5 text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <p className="text-[10px] text-[#6B7280]">
                Note: Libvirt remote connections on Windows require Linux SSH keys or libvirt remote daemon configured. For enterprise clusters, Proxmox VE REST API provides HTTPS authentication.
              </p>
            </div>
          )}
        </div>

        {/* Diagnostic Test Runner & Feedback */}
        <div className="rounded-md border border-[#1C202A] bg-[#0A0C10] p-4 mb-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-bold text-slate-200 uppercase tracking-wide flex items-center space-x-1.5">
              <Activity className="h-3.5 w-3.5 text-blue-400" />
              <span>Provider Preflight Diagnostic</span>
            </span>
            <button
              onClick={handleTestConnection}
              disabled={testingConnection}
              className="inline-flex items-center space-x-1.5 rounded border border-blue-500/40 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-400 hover:bg-blue-500/20 hover:border-blue-500 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${testingConnection ? 'animate-spin' : ''}`} />
              <span>{testingConnection ? 'TESTING...' : 'TEST CONNECTION'}</span>
            </button>
          </div>

          {testResult ? (
            <div className="space-y-2.5 pt-1">
              <div className="flex items-center justify-between border-b border-[#1C202A] pb-2">
                <span className="text-[11px] text-[#6B7280]">DIAGNOSTIC STATUS:</span>
                {getStatusBadge(testResult.status)}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px]">
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block flex items-center space-x-1">
                    <Clock className="h-2.5 w-2.5" />
                    <span>LATENCY</span>
                  </span>
                  <span className="text-white font-semibold">
                    {testResult.latency_ms !== null && testResult.latency_ms !== undefined
                      ? `${testResult.latency_ms} ms`
                      : 'N/A'}
                  </span>
                </div>
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block flex items-center space-x-1">
                    <Server className="h-2.5 w-2.5" />
                    <span>NODES</span>
                  </span>
                  <span className="text-white font-semibold">{testResult.node_count}</span>
                </div>
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A]">
                  <span className="text-[#6B7280] block flex items-center space-x-1">
                    <Cpu className="h-2.5 w-2.5" />
                    <span>WORKLOADS</span>
                  </span>
                  <span className="text-white font-semibold">{testResult.vm_count}</span>
                </div>
                <div className="rounded bg-[#14171E] p-2 border border-[#1C202A] truncate">
                  <span className="text-[#6B7280] block">VERSION</span>
                  <span className="text-white font-semibold truncate block" title={testResult.hypervisor_version || 'N/A'}>
                    {testResult.hypervisor_version || 'N/A'}
                  </span>
                </div>
              </div>

              <div className="rounded bg-[#14171E] p-2.5 border border-[#1C202A] text-[11px]">
                <span className="text-[#6B7280] block text-[10px] mb-0.5">DETAIL:</span>
                <p className={testResult.status === 'CONNECTED' ? 'text-emerald-300' : 'text-amber-300'}>
                  {testResult.message}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-[11px] text-[#6B7280] italic">
              Click &ldquo;TEST CONNECTION&rdquo; to query hypervisor status, verify API tokens, and check inventory discovery before activating.
            </p>
          )}
        </div>

        {/* Architectural Guard Warning */}
        <div className="rounded border border-amber-500/30 bg-amber-500/5 p-3 text-[11px] text-amber-300 mb-5 flex items-start space-x-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            <strong>Architectural Guard Active:</strong> When live infrastructure is selected, VMotion AI communicates directly with your hypervisor. If credentials are missing or the host is unreachable, the system prominently declares <strong>LIVE CLUSTER DISCONNECTED</strong> without falling back to simulation.
          </span>
        </div>
        </>
        ) : (
          <div className="space-y-4 mb-5 max-h-[480px] overflow-y-auto pr-1">
            <div className="rounded border border-[#1C202A] bg-[#0A0C10] p-3 text-[11px] text-[#9CA3AF] leading-relaxed">
              <span className="text-white font-semibold block mb-1">
                STRICT CLAIMS & VERIFICATION POLICY:
              </span>
              VMotion AI enforces zero false claims. Operations tested in simulation are labelled
              <strong className="text-blue-400"> TESTED LOCALLY</strong>. Code targeting physical hypervisors is labelled
              <strong className="text-purple-400"> IMPLEMENTED</strong>. Only tests verified against real physical hypervisors receive
              <strong className="text-emerald-400"> REAL INFRASTRUCTURE TESTED</strong> status.
            </div>

            {/* Matrix Table */}
            <div className="rounded border border-[#1C202A] overflow-hidden">
              <table className="w-full text-left text-[11px] font-mono border-collapse">
                <thead className="bg-[#14171E] text-[#6B7280] border-b border-[#1C202A]">
                  <tr>
                    <th className="p-2.5">OP ID</th>
                    <th className="p-2.5">OPERATION</th>
                    <th className="p-2.5">SIMULATION</th>
                    <th className="p-2.5">PROXMOX VE</th>
                    <th className="p-2.5">LIBVIRT / KVM</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1C202A] bg-[#0A0C10]">
                  {[
                    { id: 'OP-01', name: 'Node Discovery', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-02', name: 'VM Discovery', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-03', name: 'Telemetry Normalization', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-04', name: 'VM State Retrieval', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-05', name: 'Pre-Migration Validation', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-06', name: 'Live Migration Dispatch', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-07', name: 'Task Monitoring (UPID)', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-08', name: 'Placement Verification', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-09', name: 'VM Health Verification', sim: 'TESTED LOCALLY', pve: 'IMPLEMENTED', kvm: 'NOT VERIFIED' },
                    { id: 'OP-10', name: 'Preflight Diagnostic Test', sim: 'TESTED LOCALLY', pve: 'TESTED LOCALLY', kvm: 'TESTED LOCALLY' },
                    { id: 'OP-11', name: 'Disconnected Guard', sim: 'TESTED LOCALLY', pve: 'TESTED LOCALLY', kvm: 'TESTED LOCALLY' },
                  ].map((row) => (
                    <tr key={row.id} className="hover:bg-[#14171E]/50">
                      <td className="p-2.5 text-blue-400 font-bold">{row.id}</td>
                      <td className="p-2.5 text-white">{row.name}</td>
                      <td className="p-2.5">
                        <span className="rounded bg-blue-500/10 text-blue-400 px-1.5 py-0.5 border border-blue-500/30 text-[10px]">
                          {row.sim}
                        </span>
                      </td>
                      <td className="p-2.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] border ${
                          row.pve === 'TESTED LOCALLY'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                            : 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                        }`}>
                          {row.pve}
                        </span>
                      </td>
                      <td className="p-2.5">
                        <span className={`rounded px-1.5 py-0.5 text-[10px] border ${
                          row.kvm === 'TESTED LOCALLY'
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                            : 'bg-slate-500/10 text-slate-400 border-slate-500/30'
                        }`}>
                          {row.kvm}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end space-x-3 border-t border-[#1C202A] pt-4">
          <button
            onClick={onClose}
            className="rounded border border-[#2A303F] px-4 py-2 text-[#9CA3AF] hover:text-white hover:border-[#3D465C] cursor-pointer transition-colors"
          >
            CANCEL
          </button>
          <button
            onClick={handleSaveAndApply}
            disabled={loading}
            className="rounded border border-blue-500 bg-blue-600 px-5 py-2 font-semibold text-white hover:bg-blue-500 transition-colors shadow-lg cursor-pointer disabled:opacity-50 flex items-center space-x-2"
          >
            <ShieldCheck className="h-4 w-4" />
            <span>{loading ? 'APPLYING...' : 'SAVE & APPLY PROVIDER'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
