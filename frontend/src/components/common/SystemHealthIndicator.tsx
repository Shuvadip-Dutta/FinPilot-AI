import React, { useEffect, useState } from 'react';
import { authApi } from '../../api/auth';
import { HealthResponse } from '../../types/api';
import { Activity } from 'lucide-react';

// Shared cache/promise across all mounted SystemHealthIndicator instances
let inFlightHealthPromise: Promise<HealthResponse> | null = null;
let lastHealthFetchTime = 0;
let cachedHealthResponse: HealthResponse | null = null;

async function getCachedHealth(): Promise<HealthResponse> {
  const now = Date.now();
  if (cachedHealthResponse && now - lastHealthFetchTime < 5000) {
    return cachedHealthResponse;
  }
  if (inFlightHealthPromise) {
    return inFlightHealthPromise;
  }
  inFlightHealthPromise = authApi
    .getHealth()
    .then((res) => {
      cachedHealthResponse = res;
      lastHealthFetchTime = Date.now();
      inFlightHealthPromise = null;
      return res;
    })
    .catch((err) => {
      cachedHealthResponse = null;
      inFlightHealthPromise = null;
      throw err;
    });
  return inFlightHealthPromise;
}

export const SystemHealthIndicator: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<'operational' | 'degraded' | 'unavailable' | 'checking'>('checking');

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const res = await getCachedHealth();
        if (!isMounted) return;
        setHealth(res);
        const lower = String(res.status || '').toLowerCase();
        if (lower === 'ok' || lower === 'healthy' || lower === 'operational') {
          setStatus('operational');
        } else if (lower === 'degraded') {
          setStatus('degraded');
        } else {
          setStatus('operational');
        }
      } catch {
        if (!isMounted) return;
        setStatus('unavailable');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll health every 30s

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const config = {
    checking: {
      dot: 'bg-status-warning animate-pulse',
      text: 'Checking...',
      label: 'Connecting to Django API',
    },
    operational: {
      dot: 'bg-status-positive',
      text: 'API Online',
      label: 'Django Backend Operational',
    },
    degraded: {
      dot: 'bg-status-warning',
      text: 'Degraded',
      label: 'Services Operating with Partial Degradation',
    },
    unavailable: {
      dot: 'bg-status-negative',
      text: 'Offline',
      label: 'Django API Offline',
    },
  }[status];

  if (compact) {
    return (
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-secondary/70 border border-border-theme text-xs text-text-secondary"
        title={config.label}
      >
        <span className={`w-2 h-2 rounded-full ${config.dot}`} />
        <span className="font-mono text-[11px]">{config.text}</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-secondary/70 border border-border-theme text-xs"
      title={`${config.label}${health?.version ? ` (v${health.version})` : ''}`}
    >
      <Activity className="w-3.5 h-3.5 text-text-muted" />
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      <span className="text-text-secondary font-medium">Django API:</span>
      <span className="font-mono text-text-muted">{config.text}</span>
    </div>
  );
};
