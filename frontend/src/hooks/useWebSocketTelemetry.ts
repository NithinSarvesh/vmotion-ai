import { useState, useEffect, useRef, useCallback } from 'react';
import type {
  ClusterState,
  Recommendation,
  SafetyEvaluation,
  PendingProposal,
  MigrationTaskStatus,
  AuditEntry,
  TelemetryPulsePayload,
  AggregatedClusterTelemetry,
  PPOModelHealth
} from '../types';

export function useWebSocketTelemetry() {
  const [cluster, setCluster] = useState<ClusterState | null>(null);
  const [telemetry, setTelemetry] = useState<AggregatedClusterTelemetry | null>(null);
  const [modelHealth, setModelHealth] = useState<PPOModelHealth | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [safetyEvaluation, setSafetyEvaluation] = useState<SafetyEvaluation | null>(null);
  const [proposals, setProposals] = useState<PendingProposal[]>([]);
  const [activeTasks, setActiveTasks] = useState<MigrationTaskStatus[]>([]);
  const [completedTasks, setCompletedTasks] = useState<MigrationTaskStatus[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const fetchRestState = useCallback(async () => {
    try {
      const [clusterRes, telemetryRes, healthRes, aiRes, tasksRes, auditRes] = await Promise.all([
        fetch('/api/cluster/state').then((r) => r.ok ? r.json() : null),
        fetch('/api/cluster/telemetry').then((r) => r.ok ? r.json() : null),
        fetch('/api/ai/model/health').then((r) => r.ok ? r.json() : null),
        fetch('/api/ai/recommendation').then((r) => r.ok ? r.json() : null),
        fetch('/api/migrations/tasks').then((r) => r.ok ? r.json() : null),
        fetch('/api/audit/logs?limit=25').then((r) => r.ok ? r.json() : null)
      ]);

      if (clusterRes) setCluster(clusterRes);
      if (telemetryRes) setTelemetry(telemetryRes);
      if (healthRes) setModelHealth(healthRes);
      if (aiRes) {
        setRecommendation(aiRes.recommendation);
        setSafetyEvaluation(aiRes.safety_evaluation);
      }
      if (tasksRes) {
        setActiveTasks(tasksRes.active || []);
        setCompletedTasks(tasksRes.completed || []);
        setProposals(tasksRes.pending_proposals || []);
      }
      if (auditRes) {
        setAuditEntries(auditRes);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to reach VMotion AI backend');
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/telemetry`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const payload: TelemetryPulsePayload = JSON.parse(event.data);
          if (payload.type === 'TELEMETRY_PULSE') {
            setCluster(payload.cluster);
            if (payload.telemetry) setTelemetry(payload.telemetry);
            if (payload.model_health) setModelHealth(payload.model_health);
            setRecommendation(payload.recommendation);
            setSafetyEvaluation(payload.safety_evaluation);
            setProposals(payload.proposals || []);
            setActiveTasks(payload.active_tasks || []);
            setCompletedTasks(payload.completed_tasks || []);
            setAuditEntries(payload.audit_entries || []);
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        wsRef.current = null;
        reconnectTimeoutRef.current = window.setTimeout(connectWebSocket, 2500);
      };

      ws.onerror = () => {
        setWsConnected(false);
        ws.close();
      };
    } catch {
      setWsConnected(false);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    fetchRestState();

    const fallbackInterval = setInterval(() => {
      if (!wsConnected) {
        fetchRestState();
      }
    }, 3000);

    return () => {
      clearInterval(fallbackInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket, fetchRestState, wsConnected]);

  const approveProposal = async (proposalId: string) => {
    try {
      const res = await fetch(`/api/migrations/approve/${proposalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Authorized via Operator UI' })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Approval failed');
      }
      await fetchRestState();
      return true;
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
      return false;
    }
  };

  const rejectProposal = async (proposalId: string, reason?: string) => {
    try {
      const res = await fetch(`/api/migrations/reject/${proposalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || 'Declined by human operator' })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Rejection failed');
      }
      await fetchRestState();
      return true;
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
      return false;
    }
  };

  const cancelProposal = async (proposalId: string, reason?: string) => {
    try {
      const res = await fetch(`/api/migrations/cancel/${proposalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || 'Cancelled by operator' })
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Cancellation failed');
      }
      await fetchRestState();
      return true;
    } catch (err: any) {
      alert(`Cancellation error: ${err.message}`);
      return false;
    }
  };

  const switchProviderMode = async (providerType: 'simulation' | 'proxmox' | 'libvirt') => {
    try {
      const res = await fetch('/api/cluster/mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Operator-Key': 'vmotion-operator-key-default'
        },
        body: JSON.stringify({
          provider_type: providerType,
          confirm_live: providerType !== 'simulation'
        })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to switch provider');
      }
      await fetchRestState();
    } catch (err: any) {
      alert(`Provider mode error: ${err.message}`);
    }
  };

  return {
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
    error,
    actions: {
      approveProposal,
      rejectProposal,
      cancelProposal,
      switchProviderMode,
      refresh: fetchRestState
    }
  };
}
