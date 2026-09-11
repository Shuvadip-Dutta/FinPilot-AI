import React, { useEffect, useState } from 'react';
import { authApi } from '../../api/auth';
import { HealthResponse } from '../../types/api';
import { Activity } from 'lucide-react';

export const SystemHealthIndicator: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<'operational' | 'degraded' | 'unavailable' | 'checking'>('checking');

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const res = await authApi.getHealth();
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
      dot: 'bg-amber-400 animate-pulse',
      text: 'Checking...',
      label: 'Connecting to Django API',
    },
    operational: {
      dot: 'bg-emerald-400',
      text: 'API Online',
      label: 'Django Backend Operational',
    },
    degraded: {
      dot: 'bg-amber-400',
      text: 'Degraded',
      label: 'Services Operating with Partial Degradation',
    },
    unavailable: {
      dot: 'bg-rose-400',
      text: 'Offline',
      label: 'Django API Offline (http://127.0.0.1:8000)',
    },
  }[status];

  if (compact) {
    return (
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs text-slate-300"
        title={config.label}
      >
        <span className={`w-2 h-2 rounded-full ${config.dot}`} />
        <span className="font-mono text-[11px]">{config.text}</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800/80 text-xs"
      title={`${config.label}${health?.version ? ` (v${health.version})` : ''}`}
    >
      <Activity className="w-3.5 h-3.5 text-slate-400" />
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      <span className="text-slate-300 font-medium">Django API:</span>
      <span className="font-mono text-slate-400">{config.text}</span>
    </div>
  );
};
