import React, { useState, useEffect } from 'react';
import { 
  Laptop, 
  Server, 
  Download, 
  Copy, 
  Check, 
  RefreshCw, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  Cpu, 
  ShieldCheck, 
  Zap, 
  Info 
} from 'lucide-react';
import type { Device, PublishedVM, MigrationJob, ClusterState, AgentSessionInfo } from '../types';

interface RoleSelectorSectionProps {
  cluster: ClusterState | null;
  agents?: AgentSessionInfo[];
  onTriggerRefresh?: () => void;
}

export const RoleSelectorSection: React.FC<RoleSelectorSectionProps> = ({
  cluster,
  agents = [],
  onTriggerRefresh
}) => {
  const [activeTab, setActiveTab] = useState<'source' | 'target' | 'same-computer'>('same-computer');
  const [devices, setDevices] = useState<Device[]>([]);
  const [publishedVms, setPublishedVms] = useState<PublishedVM[]>([]);
  const [, setMigrationJobs] = useState<MigrationJob[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  // Authentication & Enrollment Secrets
  const [operatorKey, setOperatorKey] = useState<string>(() => localStorage.getItem('vmotion_operator_key') || '');
  const [enrollSecret, setEnrollSecret] = useState<string>('');
  const effectiveSecret = enrollSecret.trim() || '<ENROLLMENT_SECRET>';

  // Forms
  const [publishVmName, setPublishVmName] = useState<string>('VMotion-Demo');
  const [publishDeviceId, setPublishDeviceId] = useState<string>('');
  const [selectedVmForMigration, setSelectedVmForMigration] = useState<string>('');
  const [targetDeviceId, setTargetDeviceId] = useState<string>('');
  const [sameComputerVm, setSameComputerVm] = useState<string>('VMotion-Demo');
  const [migrationSubmitting, setMigrationSubmitting] = useState<boolean>(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<MigrationJob | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const serverUrl = window.location.origin;

  const handleOperatorKeyChange = (key: string) => {
    setOperatorKey(key);
    localStorage.setItem('vmotion_operator_key', key);
  };

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const opHeaders: Record<string, string> = operatorKey ? { 'X-Operator-Key': operatorKey } : {};
      const [devRes, vmRes, jobRes] = await Promise.all([
        fetch('/api/devices', { headers: opHeaders }),
        fetch('/api/catalog/vms'),
        fetch('/api/migrations/jobs', { headers: opHeaders })
      ]);

      if (devRes.ok) {
        const devData = await devRes.json();
        setDevices(devData);
        if (devData.length > 0 && !publishDeviceId) {
          setPublishDeviceId(devData[0].device_id);
        }
        if (devData.length > 0 && !targetDeviceId) {
          const tgt = devData.find((d: Device) => d.role === 'target' || d.role === 'both');
          if (tgt) setTargetDeviceId(tgt.device_id);
        }
      }

      if (vmRes.ok) {
        const vmData = await vmRes.json();
        setPublishedVms(vmData);
        if (vmData.length > 0 && !selectedVmForMigration) {
          setSelectedVmForMigration(vmData[0].name);
        }
      }

      if (jobRes.ok) {
        const jobData = await jobRes.json();
        setMigrationJobs(jobData);
        if (activeJobId) {
          const found = jobData.find((j: MigrationJob) => j.job_id === activeJobId);
          if (found) setActiveJob(found);
        } else if (jobData.length > 0) {
          const latest = jobData[0];
          if (['QUEUED', 'PREPARING', 'MIGRATING', 'VERIFYING'].includes(latest.state)) {
            setActiveJob(latest);
            setActiveJobId(latest.job_id);
          }
        }
      }
    } catch (err) {
      console.error('Error fetching devices/catalog:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [activeJobId]);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(label);
    setTimeout(() => setCopiedCmd(null), 2500);
  };

  const handlePublishVm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publishVmName || !publishDeviceId) {
      setStatusMessage({ type: 'error', text: 'Please specify a VM name and select a host device.' });
      return;
    }

    try {
      const res = await fetch('/api/catalog/publish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(operatorKey ? { 'X-Operator-Key': operatorKey } : {})
        },
        body: JSON.stringify({
          device_id: publishDeviceId,
          vm_name: publishVmName
        })
      });

      if (res.ok) {
        setStatusMessage({ type: 'success', text: `VM '${publishVmName}' successfully published to catalog!` });
        fetchData();
      } else {
        const data = await res.json();
        setStatusMessage({ type: 'error', text: data.detail || 'Failed to publish VM.' });
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Error: ${err}` });
    }
  };

  const handleUnpublishVm = async (deviceId: string, vmName: string) => {
    try {
      const res = await fetch('/api/catalog/unpublish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(operatorKey ? { 'X-Operator-Key': operatorKey } : {})
        },
        body: JSON.stringify({ device_id: deviceId, vm_name: vmName })
      });
      if (res.ok) {
        setStatusMessage({ type: 'info', text: `Unpublished VM '${vmName}'.` });
        fetchData();
      }
    } catch (err) {
      console.error('Failed to unpublish VM:', err);
    }
  };

  const handleRevokeDevice = async (deviceId: string) => {
    if (!window.confirm(`Revoke device '${deviceId}'? The agent will be disconnected.`)) return;
    try {
      const res = await fetch(`/api/devices/${deviceId}`, {
        method: 'DELETE',
        headers: operatorKey ? { 'X-Operator-Key': operatorKey } : {}
      });
      if (res.ok) {
        setStatusMessage({ type: 'info', text: `Device '${deviceId}' revoked.` });
        fetchData();
      }
    } catch (err) {
      console.error('Failed to revoke device:', err);
    }
  };

  const handleTriggerMigration = async (isSameComputer: boolean = false) => {
    setMigrationSubmitting(true);
    setStatusMessage(null);

    let srcDevice = '';
    let tgtDevice = '';
    let vmName = '';

    if (isSameComputer) {
      // Find an online device or use default local device
      const onlineDev = devices.find(d => d.status === 'online') || devices[0];
      srcDevice = onlineDev ? onlineDev.device_id : 'vbox-host-a';
      tgtDevice = srcDevice;
      vmName = sameComputerVm;
    } else {
      const pub = publishedVms.find(v => v.name === selectedVmForMigration);
      if (!pub) {
        setStatusMessage({ type: 'error', text: 'Selected VM is not in the catalog.' });
        setMigrationSubmitting(false);
        return;
      }
      srcDevice = pub.device_id;
      tgtDevice = targetDeviceId;
      vmName = selectedVmForMigration;
    }

    try {
      const res = await fetch('/api/migrations/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(operatorKey ? { 'X-Operator-Key': operatorKey } : {})
        },
        body: JSON.stringify({
          source_device_id: srcDevice,
          target_device_id: tgtDevice,
          vm_name: vmName,
          direct_transfer_method: isSameComputer ? 'same_host' : 'direct_lan',
          auto_start_target: true
        })
      });

      if (res.ok) {
        const job = await res.json();
        setActiveJobId(job.job_id);
        setActiveJob(job);
        setStatusMessage({ 
          type: 'success', 
          text: `Migration job '${job.job_id}' started! Monitoring progress below.` 
        });
        fetchData();
        if (onTriggerRefresh) onTriggerRefresh();
      } else {
        const errData = await res.json();
        setStatusMessage({ type: 'error', text: errData.detail || 'Failed to trigger migration.' });
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Network error: ${err}` });
    } finally {
      setMigrationSubmitting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-[#E2E8F0] gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="flex h-2 w-2 rounded-full bg-blue-600" />
            <h2 className="text-xl font-bold tracking-tight text-[#0F172A]">Physical Host Onboarding &amp; Migration</h2>
            <span className="rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-[11px] font-mono font-semibold text-blue-700">
              {cluster?.is_live ? 'LIVE HYPERVISOR' : 'CONTROL PLANE'} • {agents.length} AGENT(S) ONLINE
            </span>
          </div>
          <p className="mt-1 text-xs text-[#64748B]">
            Connect your physical Windows laptops to this control plane using the standalone VMotion Agent or run single-laptop verification.
          </p>
        </div>

        {/* Global Agent Download Button */}
        <div className="flex items-center space-x-3">
          <a
            href="/api/agent/download"
            download="vmotion-agent.exe"
            className="inline-flex items-center space-x-2 rounded-lg bg-blue-600 px-4 py-2 font-mono text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors cursor-pointer"
          >
            <Download className="h-4 w-4" />
            <span>DOWNLOAD WINDOWS AGENT (.EXE)</span>
          </a>

          <button
            onClick={fetchData}
            disabled={isLoading}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-[#CBD5E1] bg-[#F8FAFC] px-3 py-2 font-mono text-xs text-[#475569] hover:bg-white transition-colors cursor-pointer"
            title="Refresh Registry &amp; Catalog"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* Control Plane Security & Credentials Panel */}
      <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/30 p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-[11px] font-mono font-semibold text-[#334155] mb-1">
              OPERATOR ADMIN KEY (X-Operator-Key)
            </label>
            <input
              type="password"
              value={operatorKey}
              onChange={(e) => handleOperatorKeyChange(e.target.value)}
              placeholder="Enter operator key for administrative actions"
              className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs font-mono text-[#0F172A] focus:border-blue-600 focus:outline-hidden"
            />
          </div>
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-[11px] font-mono font-semibold text-[#334155] mb-1">
              ENROLLMENT SECRET (To populate agent commands)
            </label>
            <input
              type="password"
              value={enrollSecret}
              onChange={(e) => setEnrollSecret(e.target.value)}
              placeholder="Optional: Enter secret to fill copy snippets"
              className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs font-mono text-[#0F172A] focus:border-blue-600 focus:outline-hidden"
            />
          </div>
        </div>
      </div>

      {/* Role Mode Tabs */}
      <div className="mt-6 flex border-b border-[#E2E8F0]">
        <button
          onClick={() => setActiveTab('same-computer')}
          className={`flex items-center space-x-2 border-b-2 px-5 py-3 text-xs font-mono font-semibold transition-all cursor-pointer ${
            activeTab === 'same-computer'
              ? 'border-emerald-600 text-emerald-800 bg-emerald-50/40'
              : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
          }`}
        >
          <Zap className="h-4 w-4 text-emerald-600" />
          <span>SAME-COMPUTER TESTING (SINGLE LAPTOP)</span>
        </button>

        <button
          onClick={() => setActiveTab('source')}
          className={`flex items-center space-x-2 border-b-2 px-5 py-3 text-xs font-mono font-semibold transition-all cursor-pointer ${
            activeTab === 'source'
              ? 'border-blue-600 text-blue-800 bg-blue-50/40'
              : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
          }`}
        >
          <Laptop className="h-4 w-4 text-blue-600" />
          <span>SOURCE COMPUTER (HOST ONBOARDING)</span>
        </button>

        <button
          onClick={() => setActiveTab('target')}
          className={`flex items-center space-x-2 border-b-2 px-5 py-3 text-xs font-mono font-semibold transition-all cursor-pointer ${
            activeTab === 'target'
              ? 'border-indigo-600 text-indigo-800 bg-indigo-50/40'
              : 'border-transparent text-[#64748B] hover:text-[#0F172A]'
          }`}
        >
          <Server className="h-4 w-4 text-indigo-600" />
          <span>TARGET COMPUTER (DESTINATION)</span>
        </button>
      </div>

      {/* Status Messages */}
      {statusMessage && (
        <div className={`mt-4 flex items-center space-x-2 rounded-lg p-3 text-xs font-mono border ${
          statusMessage.type === 'success' 
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : statusMessage.type === 'error'
            ? 'bg-red-50 border-red-200 text-red-800'
            : 'bg-blue-50 border-blue-200 text-blue-800'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          ) : statusMessage.type === 'error' ? (
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
          ) : (
            <Info className="h-4 w-4 text-blue-600 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* TAB 1: SAME-COMPUTER TESTING (SINGLE LAPTOP MODE) */}
      {activeTab === 'same-computer' && (
        <div className="mt-6 space-y-6">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
            <div className="flex items-start space-x-3">
              <Zap className="h-5 w-5 text-emerald-700 mt-0.5 shrink-0" />
              <div>
                <h3 className="text-sm font-bold text-emerald-950 font-mono">
                  Real Cold Migration Demonstration — Same-Computer Testing Mode
                </h3>
                <p className="mt-1 text-xs text-emerald-900 leading-relaxed">
                  Demonstrates the authentic, non-simulated 9-stage VirtualBox OVA export, cryptographic SHA-256 verification, 
                  and appliance import on your single Windows laptop without requiring a second machine. The agent exports your 
                  VM to an OVA package, verifies its SHA-256 digest, and re-imports it cleanly into Oracle VirtualBox.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#0F172A]">1. Launch VMotion Agent Locally</span>
                <span className="rounded bg-emerald-100 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-800">
                  {devices.some(d => d.status === 'online') ? 'AGENT ONLINE' : 'AGENT WAITING'}
                </span>
              </div>
              <p className="text-xs text-[#64748B]">
                Run this command in PowerShell from the project root or folder containing <code className="bg-white px-1 border rounded">vmotion-agent.exe</code>:
              </p>
              <div className="relative rounded-lg bg-[#0F172A] p-3 font-mono text-xs text-emerald-400 overflow-x-auto">
                <code>.\dist\vmotion-agent.exe --server {serverUrl} --enroll {effectiveSecret} --role both</code>
                <button
                  onClick={() => handleCopy(`.\\dist\\vmotion-agent.exe --server ${serverUrl} --enroll ${effectiveSecret} --role both`, 'same-cmd')}
                  className="absolute right-2 top-2 rounded bg-white/10 p-1.5 text-white hover:bg-white/20 transition-colors"
                  title="Copy command"
                >
                  {copiedCmd === 'same-cmd' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
              <div className="text-[11px] text-[#64748B] flex items-center space-x-1.5">
                <Info className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                <span>Or run with python: <code className="bg-white px-1 border rounded text-[#0F172A]">python vmotion-agent/agent.py --server {serverUrl} --enroll {effectiveSecret}</code></span>
              </div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4 flex flex-col justify-between">
              <div>
                <span className="font-mono text-xs font-bold text-[#0F172A]">2. Select VM &amp; Execute Real Migration</span>
                <p className="mt-1 text-xs text-[#64748B]">
                  Choose your registered VirtualBox VM on this laptop:
                </p>
                <div className="mt-3">
                  <label className="block text-[11px] font-mono text-[#475569] mb-1">LOCAL VM NAME</label>
                  <input
                    type="text"
                    value={sameComputerVm}
                    onChange={(e) => setSameComputerVm(e.target.value)}
                    placeholder="VMotion-Demo"
                    className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-mono text-[#0F172A] focus:border-emerald-600 focus:outline-hidden"
                  />
                  <span className="text-[10px] text-[#94A3B8] mt-1 block">Default created by setup: "VMotion-Demo"</span>
                </div>
              </div>

              <button
                onClick={() => handleTriggerMigration(true)}
                disabled={migrationSubmitting}
                className="w-full inline-flex items-center justify-center space-x-2 rounded-lg bg-emerald-600 px-4 py-2.5 font-mono text-xs font-bold text-white shadow-xs hover:bg-emerald-700 transition-colors cursor-pointer disabled:opacity-50"
              >
                {migrationSubmitting ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                <span>START SAME-COMPUTER COLD MIGRATION</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SOURCE COMPUTER (HOST ONBOARDING) */}
      {activeTab === 'source' && (
        <div className="mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4">
              <span className="font-mono text-xs font-bold text-[#0F172A]">Step 1: Download &amp; Enroll Host A (Source Laptop)</span>
              <p className="text-xs text-[#64748B]">
                Run the agent executable with <code className="bg-white px-1 border rounded">--role source</code> to enroll your computer:
              </p>
              <div className="relative rounded-lg bg-[#0F172A] p-3 font-mono text-xs text-blue-400 overflow-x-auto">
                <code>.\vmotion-agent.exe --server {serverUrl} --enroll {effectiveSecret} --role source</code>
                <button
                  onClick={() => handleCopy(`.\\vmotion-agent.exe --server ${serverUrl} --enroll ${effectiveSecret} --role source`, 'src-cmd')}
                  className="absolute right-2 top-2 rounded bg-white/10 p-1.5 text-white hover:bg-white/20 transition-colors"
                >
                  {copiedCmd === 'src-cmd' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
              <p className="text-[11px] text-[#64748B]">
                The agent will dynamically discover your active Wi-Fi LAN IP, Tailscale IP, and Oracle VirtualBox version.
              </p>
            </div>

            <form onSubmit={handlePublishVm} className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4">
              <span className="font-mono text-xs font-bold text-[#0F172A]">Step 2: Publish VM to Migration Catalog</span>
              <div>
                <label className="block text-[11px] font-mono text-[#475569] mb-1">SELECT ENROLLED HOST</label>
                <select
                  value={publishDeviceId}
                  onChange={(e) => setPublishDeviceId(e.target.value)}
                  className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-mono text-[#0F172A]"
                >
                  {devices.map(d => (
                    <option key={d.device_id} value={d.device_id}>
                      {d.hostname} ({d.device_id}) — {d.status.toUpperCase()}
                    </option>
                  ))}
                  {devices.length === 0 && (
                    <option value="vbox-host-a">vbox-host-a (Default Local Host)</option>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#475569] mb-1">VIRTUAL MACHINE NAME</label>
                <input
                  type="text"
                  value={publishVmName}
                  onChange={(e) => setPublishVmName(e.target.value)}
                  placeholder="VMotion-Demo"
                  className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-mono text-[#0F172A]"
                />
              </div>

              <button
                type="submit"
                className="w-full inline-flex items-center justify-center space-x-2 rounded-lg bg-blue-600 px-4 py-2 font-mono text-xs font-bold text-white hover:bg-blue-700 transition-colors cursor-pointer"
              >
                <span>PUBLISH VM TO CATALOG</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 3: TARGET COMPUTER (DESTINATION) */}
      {activeTab === 'target' && (
        <div className="mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4">
              <span className="font-mono text-xs font-bold text-[#0F172A]">Step 1: Enroll Target Computer (Host B)</span>
              <p className="text-xs text-[#64748B]">
                On the destination laptop, run the agent with <code className="bg-white px-1 border rounded">--role target</code>:
              </p>
              <div className="relative rounded-lg bg-[#0F172A] p-3 font-mono text-xs text-indigo-400 overflow-x-auto">
                <code>.\vmotion-agent.exe --server {serverUrl} --enroll {effectiveSecret} --role target</code>
                <button
                  onClick={() => handleCopy(`.\\vmotion-agent.exe --server ${serverUrl} --enroll ${effectiveSecret} --role target`, 'tgt-cmd')}
                  className="absolute right-2 top-2 rounded bg-white/10 p-1.5 text-white hover:bg-white/20 transition-colors"
                >
                  {copiedCmd === 'tgt-cmd' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-4 flex flex-col justify-between">
              <div>
                <span className="font-mono text-xs font-bold text-[#0F172A]">Step 2: Select Published VM &amp; Destination Host</span>
                <div className="mt-3 space-y-3">
                  <div>
                    <label className="block text-[11px] font-mono text-[#475569] mb-1">SELECT PUBLISHED VM</label>
                    <select
                      value={selectedVmForMigration}
                      onChange={(e) => setSelectedVmForMigration(e.target.value)}
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-mono text-[#0F172A]"
                    >
                      {publishedVms.map(v => (
                        <option key={v.vm_id} value={v.name}>
                          {v.name} (Source: {v.hostname || v.device_id})
                        </option>
                      ))}
                      {publishedVms.length === 0 && (
                        <option value="">No published VMs available in catalog</option>
                      )}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-[#475569] mb-1">SELECT TARGET DESTINATION HOST</label>
                    <select
                      value={targetDeviceId}
                      onChange={(e) => setTargetDeviceId(e.target.value)}
                      className="w-full rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-mono text-[#0F172A]"
                    >
                      {devices.filter(d => d.role === 'target' || d.role === 'both').map(d => (
                        <option key={d.device_id} value={d.device_id}>
                          {d.hostname} ({d.device_id}) — {d.status.toUpperCase()}
                        </option>
                      ))}
                      {devices.length === 0 && (
                        <option value="vbox-host-b">vbox-host-b (Default Target)</option>
                      )}
                    </select>
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleTriggerMigration(false)}
                disabled={migrationSubmitting || publishedVms.length === 0}
                className="w-full inline-flex items-center justify-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2.5 font-mono text-xs font-bold text-white hover:bg-indigo-700 transition-colors cursor-pointer disabled:opacity-50"
              >
                {migrationSubmitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                <span>EXECUTE TWO-COMPUTER COLD MIGRATION</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Migration Progress Tracker (if a job is active) */}
      {activeJob && (
        <div className="mt-8 rounded-xl border border-blue-200 bg-blue-50/50 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className={`h-2.5 w-2.5 rounded-full ${activeJob.state === 'COMPLETED' ? 'bg-emerald-500' : activeJob.state === 'FAILED' ? 'bg-red-500' : 'bg-blue-600 animate-ping'}`} />
              <span className="font-mono text-xs font-bold text-[#0F172A]">
                MIGRATION JOB {activeJob.job_id.toUpperCase()} — {activeJob.stage}
              </span>
            </div>
            <span className="font-mono text-xs font-bold text-blue-700">
              {activeJob.progress_percent.toFixed(0)}%
            </span>
          </div>

          <div className="h-2 w-full rounded-full bg-blue-200 overflow-hidden">
            <div 
              className="h-full bg-blue-600 transition-all duration-500"
              style={{ width: `${activeJob.progress_percent}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-[11px] text-[#475569]">
            <div>
              <span className="text-[#94A3B8] block">SOURCE:</span>
              <span className="font-semibold text-[#0F172A]">{activeJob.source_device_id}</span>
            </div>
            <div>
              <span className="text-[#94A3B8] block">TARGET:</span>
              <span className="font-semibold text-[#0F172A]">{activeJob.target_device_id}</span>
            </div>
            <div>
              <span className="text-[#94A3B8] block">FILE SIZE:</span>
              <span className="font-semibold text-[#0F172A]">{activeJob.file_size_mb ? `${activeJob.file_size_mb} MB` : 'Calculating...'}</span>
            </div>
            <div>
              <span className="text-[#94A3B8] block">SHA-256 DIGEST:</span>
              <span className="font-semibold text-[#0F172A]" title={activeJob.sha256 || ''}>
                {activeJob.sha256 ? `${activeJob.sha256.substring(0, 12)}...` : 'Pending...'}
              </span>
            </div>
          </div>
          {activeJob.error_message && (
            <div className="text-xs text-red-600 font-mono">
              Error: {activeJob.error_message}
            </div>
          )}
        </div>
      )}

      {/* Persistent Enrolled Devices Registry Table */}
      <div className="mt-8 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs font-bold text-[#0F172A] flex items-center space-x-2">
            <ShieldCheck className="h-4 w-4 text-blue-600" />
            <span>ENROLLED DEVICE REGISTRY ({devices.length})</span>
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[#E2E8F0]">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B]">
              <tr>
                <th className="py-2.5 px-4">DEVICE ID</th>
                <th className="py-2.5 px-4">HOSTNAME</th>
                <th className="py-2.5 px-4">ROLE</th>
                <th className="py-2.5 px-4">STATUS</th>
                <th className="py-2.5 px-4">LAN IP</th>
                <th className="py-2.5 px-4">VBOX VERSION</th>
                <th className="py-2.5 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0] text-[#0F172A]">
              {devices.map(d => (
                <tr key={d.device_id} className="hover:bg-[#F8FAFC]/50">
                  <td className="py-2.5 px-4 font-semibold text-blue-700">{d.device_id}</td>
                  <td className="py-2.5 px-4">{d.hostname}</td>
                  <td className="py-2.5 px-4 uppercase text-[#64748B]">{d.role}</td>
                  <td className="py-2.5 px-4">
                    <span className={`inline-flex items-center space-x-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      d.status === 'online' ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-700'
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${d.status === 'online' ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                      <span>{d.status.toUpperCase()}</span>
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-[#64748B]">{d.lan_ip || '—'}</td>
                  <td className="py-2.5 px-4 text-[#64748B]">{d.vbox_version || '7.x'}</td>
                  <td className="py-2.5 px-4 text-right">
                    <button
                      onClick={() => handleRevokeDevice(d.device_id)}
                      className="text-red-500 hover:text-red-700 cursor-pointer"
                      title="Revoke Enrollment"
                    >
                      <Trash2 className="h-3.5 w-3.5 inline" />
                    </button>
                  </td>
                </tr>
              ))}
              {devices.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-xs text-[#94A3B8]">
                    No external devices enrolled yet. Run the agent command above to enroll.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Published VM Catalog Table */}
      <div className="mt-8 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs font-bold text-[#0F172A] flex items-center space-x-2">
            <Cpu className="h-4 w-4 text-indigo-600" />
            <span>PUBLISHED VM CATALOG ({publishedVms.length})</span>
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[#E2E8F0]">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[#64748B]">
              <tr>
                <th className="py-2.5 px-4">VM NAME</th>
                <th className="py-2.5 px-4">HOST DEVICE</th>
                <th className="py-2.5 px-4">VCPU</th>
                <th className="py-2.5 px-4">RAM</th>
                <th className="py-2.5 px-4">DISK</th>
                <th className="py-2.5 px-4">GUEST STATE</th>
                <th className="py-2.5 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0] text-[#0F172A]">
              {publishedVms.map(vm => (
                <tr key={vm.vm_id} className="hover:bg-[#F8FAFC]/50">
                  <td className="py-2.5 px-4 font-semibold text-[#0F172A]">{vm.name}</td>
                  <td className="py-2.5 px-4 text-blue-700">{vm.hostname || vm.device_id}</td>
                  <td className="py-2.5 px-4">{vm.cpu_cores} Cores</td>
                  <td className="py-2.5 px-4">{vm.ram_mb} MB</td>
                  <td className="py-2.5 px-4">{vm.disk_gb} GB</td>
                  <td className="py-2.5 px-4">
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] text-gray-700 uppercase font-semibold">
                      {vm.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <button
                      onClick={() => handleUnpublishVm(vm.device_id, vm.name)}
                      className="text-[#64748B] hover:text-red-600 cursor-pointer text-[11px]"
                    >
                      Unpublish
                    </button>
                  </td>
                </tr>
              ))}
              {publishedVms.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-xs text-[#94A3B8]">
                    No VMs published to the catalog. Publish your VM from Host A to see it here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
