import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  AlertTriangle,
  Check,
  Activity,
  Server,
  RefreshCw
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
  const [proxmoxUser, setProxmoxUser] = useState<string>('vmotion-api@pve');
  const [proxmoxTokenId, setProxmoxTokenId] = useState<string>('automation');
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
            setProxmoxUser(data.proxmox.user || 'vmotion-api@pve');
            setProxmoxTokenId(data.proxmox.token_id || 'automation');
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

      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
      } else {
        const err = await res.json();
        setTestResult({
          provider: selectedProvider,
          status: 'DISCONNECTED',
          message: err.detail || 'Connection diagnostic request failed.',
          node_count: 0,
          vm_count: 0
        });
      }
    } catch (e: any) {
      setTestResult({
        provider: selectedProvider,
        status: 'DISCONNECTED',
        message: `Network error reaching control plane API: ${e.message}`,
        node_count: 0,
        vm_count: 0
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveAndSwitch = async () => {
    setLoading(true);
    try {
      // 1. Save config
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

      await fetch('/api/cluster/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configPayload)
      });

      // 2. Switch provider via parent handler
      await onSwitchProvider(selectedProvider);
      onClose();
    } catch (e) {
      console.error('Failed to switch provider:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl border border-[#CBD5E1] bg-white p-6 sm:p-8 shadow-2xl font-mono text-xs my-8">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-5 mb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-200">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#0F172A] uppercase tracking-wide">
                INFRASTRUCTURE ENVIRONMENT SELECTOR
              </h3>
              <span className="text-[11px] text-[#64748B]">
                Configure hypervisor drivers, API token credentials, and runtime topology
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Nav Tabs */}
        <div className="flex space-x-2 border-b border-[#E2E8F0] pb-4 mb-6">
          <button
            onClick={() => setModalTab('config')}
            className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
              modalTab === 'config'
                ? 'bg-[#0F172A] text-white shadow-2xs'
                : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
            }`}
          >
            01 CONFIGURATION & CREDENTIALS
          </button>
          <button
            onClick={() => setModalTab('matrix')}
            className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-bold ${
              modalTab === 'matrix'
                ? 'bg-[#0F172A] text-white shadow-2xs'
                : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
            }`}
          >
            02 CAPABILITY & READINESS MATRIX
          </button>
        </div>

        {modalTab === 'config' ? (
          <div className="space-y-6">
            
            {/* Provider Selection Cards */}
            <div>
              <label className="block text-[11px] font-bold text-[#475569] uppercase mb-2.5">
                SELECT VIRTUALIZATION PROVIDER:
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Simulation */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProvider('simulation');
                    setTestResult(null);
                  }}
                  className={`flex flex-col p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    selectedProvider === 'simulation'
                      ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-600/20'
                      : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#0F172A]">Simulation</span>
                    {selectedProvider === 'simulation' && <Check className="h-4 w-4 text-blue-600" />}
                  </div>
                  <span className="text-[10px] text-[#64748B] mt-1">Synthetic cluster</span>
                  <span className="mt-3 text-[9px] font-bold text-emerald-700 uppercase">
                    100% READY (LOCAL)
                  </span>
                </button>

                {/* Proxmox VE */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProvider('proxmox');
                    setTestResult(null);
                  }}
                  className={`flex flex-col p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    selectedProvider === 'proxmox'
                      ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-600/20'
                      : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#0F172A]">Proxmox VE</span>
                    {selectedProvider === 'proxmox' && <Check className="h-4 w-4 text-blue-600" />}
                  </div>
                  <span className="text-[10px] text-[#64748B] mt-1">REST API v2</span>
                  <span className="mt-3 text-[9px] font-bold text-blue-700 uppercase">
                    PRIMARY LIVE DRIVER
                  </span>
                </button>

                {/* Libvirt / KVM */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProvider('libvirt');
                    setTestResult(null);
                  }}
                  className={`flex flex-col p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    selectedProvider === 'libvirt'
                      ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-600/20'
                      : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#0F172A]">Libvirt KVM</span>
                    {selectedProvider === 'libvirt' && <Check className="h-4 w-4 text-blue-600" />}
                  </div>
                  <span className="text-[10px] text-[#64748B] mt-1">Linux virsh</span>
                  <span className="mt-3 text-[9px] font-bold text-amber-700 uppercase">
                    FUTURE EXTENSION
                  </span>
                </button>
              </div>
            </div>

            {/* Provider Configuration Forms */}
            {selectedProvider === 'proxmox' && (
              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 space-y-4">
                <div className="flex items-center space-x-2 text-xs font-bold text-[#0F172A]">
                  <Server className="h-4 w-4 text-blue-600" />
                  <span>PROXMOX VE REST API v2 CREDENTIALS</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-[#64748B] uppercase mb-1">
                      Endpoint Base URL:
                    </label>
                    <input
                      type="text"
                      value={proxmoxEndpoint}
                      onChange={(e) => setProxmoxEndpoint(e.target.value)}
                      placeholder="https://192.168.1.100:8006/api2/json"
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs text-[#0F172A] focus:outline-none focus:border-blue-600"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-[#64748B] uppercase mb-1">
                      API User (Least-Privilege Token User):
                    </label>
                    <input
                      type="text"
                      value={proxmoxUser}
                      onChange={(e) => setProxmoxUser(e.target.value)}
                      placeholder="vmotion-api@pve"
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs text-[#0F172A] focus:outline-none focus:border-blue-600"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-[#64748B] uppercase mb-1">
                      API Token ID:
                    </label>
                    <input
                      type="text"
                      value={proxmoxTokenId}
                      onChange={(e) => setProxmoxTokenId(e.target.value)}
                      placeholder="automation"
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs text-[#0F172A] focus:outline-none focus:border-blue-600"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-[#64748B] uppercase mb-1">
                      API Token Secret (UUID):
                    </label>
                    <input
                      type="password"
                      value={proxmoxTokenSecret}
                      onChange={(e) => setProxmoxTokenSecret(e.target.value)}
                      placeholder={tokenConfiguredOnServer ? '•••••••••••••••• (Configured on backend)' : 'Enter token secret...'}
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs text-[#0F172A] focus:outline-none focus:border-blue-600"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-1">
                  <input
                    type="checkbox"
                    id="verifySsl"
                    checked={proxmoxVerifySsl}
                    onChange={(e) => setProxmoxVerifySsl(e.target.checked)}
                    className="rounded border-[#CBD5E1] text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="verifySsl" className="text-[11px] text-[#475569]">
                    Verify TLS/SSL Certificate (Leave unchecked for self-signed homelab certificates)
                  </label>
                </div>
              </div>
            )}

            {selectedProvider === 'libvirt' && (
              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 space-y-3">
                <div className="flex items-center space-x-2 text-xs font-bold text-[#0F172A]">
                  <Server className="h-4 w-4 text-amber-600" />
                  <span>LIBVIRT HYPERVISOR CONNECTION URI</span>
                </div>
                <div>
                  <label className="block text-[10px] text-[#64748B] uppercase mb-1">
                    Connection URI (SSH or TCP):
                  </label>
                  <input
                    type="text"
                    value={libvirtUri}
                    onChange={(e) => setLibvirtUri(e.target.value)}
                    placeholder="qemu+ssh://root@192.168.1.100/system"
                    className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs text-[#0F172A] focus:outline-none focus:border-blue-600"
                  />
                </div>
              </div>
            )}

            {/* Test Connection Diagnostic Result */}
            {testResult && (
              <div className={`p-4 rounded-xl border ${
                testResult.status === 'CONNECTED'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                  : 'border-red-200 bg-red-50 text-red-900'
              }`}>
                <div className="flex items-center space-x-2 font-bold text-xs">
                  {testResult.status === 'CONNECTED' ? (
                    <Check className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                  )}
                  <span>DIAGNOSTIC STATUS: {testResult.status}</span>
                </div>
                <p className="text-[11px] mt-1 font-sans">{testResult.message}</p>
                {testResult.latency_ms && (
                  <div className="text-[10px] text-[#64748B] mt-1 font-mono">
                    Round-trip API Latency: {testResult.latency_ms} ms · Nodes: {testResult.node_count} · VMs: {testResult.vm_count}
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-3 border-t border-[#E2E8F0]">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testingConnection}
                className="flex items-center space-x-2 rounded-lg border border-[#CBD5E1] bg-white px-4 py-2 text-xs font-semibold text-[#0F172A] hover:bg-[#F8FAFC] transition-colors cursor-pointer disabled:opacity-50"
              >
                {testingConnection ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin text-blue-600" />
                    <span>DIAGNOSING...</span>
                  </>
                ) : (
                  <>
                    <Activity className="h-3.5 w-3.5 text-blue-600" />
                    <span>TEST CONNECTIVITY</span>
                  </>
                )}
              </button>

              <div className="flex items-center space-x-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-lg border border-[#CBD5E1] bg-white px-4 py-2 text-xs font-semibold text-[#475569] hover:bg-[#F8FAFC] cursor-pointer"
                >
                  CANCEL
                </button>
                <button
                  type="button"
                  onClick={handleSaveAndSwitch}
                  disabled={loading}
                  className="flex items-center space-x-1.5 rounded-lg bg-[#0F172A] px-5 py-2 text-xs font-bold text-white hover:bg-[#1E293B] transition-colors cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'SWITCHING...' : 'APPLY & ENGAGE'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Capability Matrix Tab */
          <div className="space-y-4">
            <div className="rounded-xl border border-[#E2E8F0] overflow-hidden">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B] uppercase font-bold text-[10px]">
                  <tr>
                    <th className="p-3">Capability</th>
                    <th className="p-3">SimulationProvider</th>
                    <th className="p-3">ProxmoxVEProvider</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E2E8F0]">
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">Node Discovery</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">Telemetry Collection</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">Live Migration Dispatch</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">UPID Task Polling</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">Placement Verification</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-[#0F172A]">QEMU Guest-Agent Ping</td>
                    <td className="p-3 text-emerald-700">LOCAL TESTED</td>
                    <td className="p-3 text-blue-700 font-semibold">IMPLEMENTED</td>
                  </tr>
                  <tr className="bg-amber-50/50">
                    <td className="p-3 font-bold text-amber-900">Physical Hardware Testing</td>
                    <td className="p-3 text-[#64748B]">N/A (Synthetic)</td>
                    <td className="p-3 text-amber-800 font-bold">REAL HARDWARE UNVERIFIED</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-[11px] text-amber-900">
              <strong>Strict Engineering Boundary:</strong> Real Proxmox cluster hardware connectivity remains unverified until physical cluster hardware is provisioned and baseline manual migration succeeds.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
