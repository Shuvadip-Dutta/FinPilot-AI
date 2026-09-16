import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { LoadingSkeleton } from '../common/LoadingSkeleton';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { portfolioApi } from '../../api/portfolio';
import { Alert, AlertSeverity, AlertStatus, AlertType } from '../../types/alerts';
import { formatDate } from '../../utils/formatters';
import {
  Bell,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  RefreshCw,
  Clock,
  Filter,
  Check,
  CheckCheck,
  Activity,
  X,
} from 'lucide-react';

export interface AlertCenterProps {
  portfolioId: string | number;
  className?: string;
  onAlertCountChange?: (activeCount: number) => void;
}

export const AlertCenter: React.FC<AlertCenterProps> = ({
  portfolioId,
  className = '',
  onAlertCountChange,
}) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isMonitoring, setIsMonitoring] = useState<boolean>(false);
  const [acknowledgingIds, setAcknowledgingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Filter state
  const [statusFilter, setStatusFilter] = useState<'ALL' | AlertStatus>('ALL');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | AlertSeverity>('ALL');

  // Load alerts
  const loadAlerts = useCallback(async () => {
    if (!portfolioId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await portfolioApi.getAlerts(portfolioId);
      setAlerts(data);
      const activeCount = data.filter((a) => a.status === 'ACTIVE').length;
      onAlertCountChange?.(activeCount);
    } catch (err: any) {
      console.error('Failed to load portfolio alerts:', err);
      setError(err?.response?.data?.error || err?.message || 'Failed to retrieve alerts for this portfolio.');
    } finally {
      setIsLoading(false);
    }
  }, [portfolioId, onAlertCountChange]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  // Run on-demand monitoring
  const handleRunMonitoring = async () => {
    if (!portfolioId || isMonitoring) return;
    setIsMonitoring(true);
    setFeedback(null);
    try {
      const result = await portfolioApi.runMonitoring(portfolioId);
      const createdCount = result.alerts_created?.length ?? 0;
      const suppressedCount = result.alerts_suppressed?.length ?? 0;

      setFeedback({
        type: 'success',
        message: `Monitoring complete — ${createdCount} alert${createdCount === 1 ? '' : 's'} created, ${suppressedCount} suppressed by cooldown.`,
      });

      // Refresh alerts list
      await loadAlerts();
    } catch (err: any) {
      console.error('Failed to execute monitoring:', err);
      setFeedback({
        type: 'error',
        message: err?.response?.data?.error || err?.message || 'Failed to run on-demand portfolio monitoring.',
      });
    } finally {
      setIsMonitoring(false);
    }
  };

  // Acknowledge single alert
  const handleAcknowledge = async (alertId: string) => {
    if (acknowledgingIds.has(alertId)) return;

    setAcknowledgingIds((prev) => new Set(prev).add(alertId));
    try {
      const updatedAlert = await portfolioApi.acknowledgeAlert(portfolioId, alertId);
      setAlerts((prevAlerts) =>
        prevAlerts.map((a) => (a.id === alertId ? updatedAlert : a))
      );
      // Update active count
      setAlerts((currentAlerts) => {
        const activeCount = currentAlerts.filter((a) => a.status === 'ACTIVE').length;
        onAlertCountChange?.(activeCount);
        return currentAlerts;
      });
      setFeedback({
        type: 'success',
        message: `Alert "${updatedAlert.title}" marked as acknowledged.`,
      });
    } catch (err: any) {
      console.error('Failed to acknowledge alert:', err);
      setFeedback({
        type: 'error',
        message: err?.response?.data?.error || err?.message || 'Failed to acknowledge alert.',
      });
    } finally {
      setAcknowledgingIds((prev) => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
    }
  };

  // Metric counts
  const counts = useMemo(() => {
    return {
      total: alerts.length,
      active: alerts.filter((a) => a.status === 'ACTIVE').length,
      acknowledged: alerts.filter((a) => a.status === 'ACKNOWLEDGED').length,
      resolved: alerts.filter((a) => a.status === 'RESOLVED').length,
      critical: alerts.filter((a) => a.severity?.toLowerCase() === 'critical').length,
    };
  }, [alerts]);

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesStatus = statusFilter === 'ALL' || alert.status === statusFilter;
      const matchesSeverity =
        severityFilter === 'ALL' || alert.severity?.toLowerCase() === severityFilter.toLowerCase();
      return matchesStatus && matchesSeverity;
    });
  }, [alerts, statusFilter, severityFilter]);

  // Helper formatting functions
  const getSeverityBadgeVariant = (severity: string): 'danger' | 'warning' | 'info' | 'neutral' => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'danger';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'neutral';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return <ShieldAlert className="w-4 h-4 text-status-negative" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-status-warning" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-status-info" />;
    }
  };

  const formatAlertTypeName = (type: string): string => {
    switch (type) {
      case 'concentration_breach':
        return 'Concentration Breach';
      case 'drawdown_breach':
        return 'Max Drawdown Breach';
      case 'loss_threshold':
        return 'Severe Loss Breach';
      default:
        return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    }
  };

  return (
    <Card id="portfolio-alert-center" className={`overflow-hidden ${className}`}>
      {/* Header with Title, Stats & Run Action */}
      <div className="p-5 border-b border-border-theme flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-surface-secondary/40">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-status-warning-soft border border-status-warning/20 flex items-center justify-center text-status-warning">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
                <span>Alert Center</span>
                {counts.active > 0 && (
                  <Badge variant="danger" size="sm" dot>
                    {counts.active} Active {counts.active === 1 ? 'Breach' : 'Breaches'}
                  </Badge>
                )}
                {counts.active === 0 && !isLoading && (
                  <Badge variant="success" size="sm">
                    Healthy
                  </Badge>
                )}
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Quantitative risk breach detection, drawdown monitoring, and threshold alerts
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadAlerts}
            disabled={isLoading || isMonitoring}
            title="Refresh alerts"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleRunMonitoring}
            disabled={isMonitoring || isLoading}
            leftIcon={
              <Activity className={`w-3.5 h-3.5 ${isMonitoring ? 'animate-spin' : ''}`} />
            }
          >
            {isMonitoring ? 'Evaluating...' : 'Run Monitoring'}
          </Button>
        </div>
      </div>

      {/* Action Feedback Banner */}
      {feedback && (
        <div
          className={`px-5 py-3 text-xs flex items-center justify-between border-b ${
            feedback.type === 'success'
              ? 'bg-status-positive-soft text-status-positive border-status-positive/20'
              : 'bg-status-negative-soft text-status-negative border-status-negative/20'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-text-muted hover:text-text-primary p-0.5 rounded cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {/* Filter / Search Controls Strip */}
      <div className="px-5 py-3 border-b border-border-theme bg-surface-secondary/20 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 p-0.5 rounded-lg bg-surface border border-border-theme">
          <button
            type="button"
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
              statusFilter === 'ALL'
                ? 'bg-accent-soft text-accent-primary border border-accent-primary font-semibold shadow-xs'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            All ({counts.total})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('ACTIVE')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-warning ${
              statusFilter === 'ACTIVE'
                ? 'bg-status-warning-soft text-status-warning border border-status-warning font-semibold shadow-xs'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            Active ({counts.active})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('ACKNOWLEDGED')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-info ${
              statusFilter === 'ACKNOWLEDGED'
                ? 'bg-status-info-soft text-status-info border border-status-info font-semibold shadow-xs'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            Acknowledged ({counts.acknowledged})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('RESOLVED')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-positive ${
              statusFilter === 'RESOLVED'
                ? 'bg-status-positive-soft text-status-positive border border-status-positive font-semibold shadow-xs'
                : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
            }`}
          >
            Resolved ({counts.resolved})
          </button>
        </div>

        {/* Severity Filter Dropdown/Pills */}
        <div className="flex items-center gap-1.5">
          <span className="text-text-muted mr-1 font-mono text-[11px] uppercase tracking-wider">
            Severity:
          </span>
          {(['ALL', 'critical', 'warning', 'info'] as const).map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => setSeverityFilter(sev)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-mono capitalize transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                severityFilter === sev
                  ? 'bg-accent-soft text-accent-primary border border-accent-primary font-semibold shadow-xs'
                  : 'border border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-secondary/70'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-5">
        {/* Loading Skeletons */}
        {isLoading && alerts.length === 0 && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <LoadingSkeleton key={i} height="h-24" width="w-full" className="rounded-xl" />
            ))}
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <ErrorState
            title="Failed to Load Alerts"
            message={error}
            onRetry={loadAlerts}
          />
        )}

        {/* Global Empty State (No alerts generated yet) */}
        {!isLoading && !error && alerts.length === 0 && (
          <EmptyState
            icon={ShieldCheck}
            title="No Monitoring Breaches Detected"
            description="All quantitative portfolio metrics are within established risk limits. Run monitoring anytime to evaluate live positions against concentration, drawdown, and severe loss rules."
            actionLabel={isMonitoring ? 'Evaluating...' : 'Run Monitoring Now'}
            onAction={handleRunMonitoring}
          />
        )}

        {/* Filtered Empty State (Alerts exist, but none match current filter) */}
        {!isLoading && !error && alerts.length > 0 && filteredAlerts.length === 0 && (
          <div className="py-12 text-center text-text-muted text-sm">
            <Info className="w-8 h-8 mx-auto mb-2 text-text-muted opacity-60" />
            <p className="font-medium text-text-primary">No alerts match the selected filters.</p>
            <button
              type="button"
              onClick={() => {
                setStatusFilter('ALL');
                setSeverityFilter('ALL');
              }}
              className="mt-2 text-xs text-accent-primary hover:underline cursor-pointer"
            >
              Reset all filters
            </button>
          </div>
        )}

        {/* Alert Cards List */}
        {!isLoading && !error && filteredAlerts.length > 0 && (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => {
              const isAcknowledging = acknowledgingIds.has(alert.id);
              const isCritical = alert.severity?.toLowerCase() === 'critical';
              const isWarning = alert.severity?.toLowerCase() === 'warning';

              // Severity border accent
              const borderAccent = isCritical
                ? 'border-l-4 border-l-status-negative bg-status-negative-soft/10'
                : isWarning
                ? 'border-l-4 border-l-status-warning bg-status-warning-soft/10'
                : 'border-l-4 border-l-status-info bg-status-info-soft/10';

              return (
                <div
                  key={alert.id}
                  className={`rounded-xl border border-border-theme p-4 transition-all duration-150 ${borderAccent} hover:border-accent-primary/40`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                    {/* Left: Metadata Badges + Title & Description */}
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Severity icon and badge */}
                        <div className="flex items-center gap-1">
                          {getSeverityIcon(alert.severity)}
                          <Badge
                            variant={getSeverityBadgeVariant(alert.severity)}
                            size="sm"
                            className="uppercase font-bold tracking-wider text-[10px]"
                          >
                            {alert.severity}
                          </Badge>
                        </div>

                        {/* Alert Type */}
                        <Badge variant="neutral" size="sm">
                          {formatAlertTypeName(alert.alert_type)}
                        </Badge>

                        {/* Status Badge */}
                        {alert.status === 'ACTIVE' && (
                          <Badge variant="warning" size="sm" dot>
                            ACTIVE
                          </Badge>
                        )}
                        {alert.status === 'ACKNOWLEDGED' && (
                          <Badge variant="info" size="sm">
                            ACKNOWLEDGED
                          </Badge>
                        )}
                        {alert.status === 'RESOLVED' && (
                          <Badge variant="success" size="sm">
                            RESOLVED
                          </Badge>
                        )}

                        {/* Timestamp */}
                        <span className="flex items-center gap-1 text-[11px] text-text-muted ml-auto lg:ml-2">
                          <Clock className="w-3 h-3" />
                          {formatDate(alert.created_at, { format: 'relative' })}
                        </span>
                      </div>

                      {/* Alert Title and Message */}
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary">{alert.title}</h4>
                        <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                          {alert.message}
                        </p>
                      </div>

                      {/* Metric Comparison Grid */}
                      <div className="inline-flex items-center gap-4 pt-1 text-xs">
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-secondary border border-border-theme">
                          <span className="text-text-muted text-[11px]">Breach Metric:</span>
                          <span className="font-mono font-semibold text-text-primary">
                            {alert.metric_value}%
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-secondary border border-border-theme">
                          <span className="text-text-muted text-[11px]">Threshold:</span>
                          <span className="font-mono font-medium text-text-muted">
                            {alert.threshold_value}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right: Actions & State */}
                    <div className="flex items-center lg:items-end flex-col justify-between shrink-0 gap-2 pt-2 lg:pt-0 border-t lg:border-t-0 border-border-theme">
                      {alert.status === 'ACTIVE' && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleAcknowledge(alert.id)}
                          disabled={isAcknowledging}
                          leftIcon={
                            isAcknowledging ? (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Check className="w-3.5 h-3.5 text-status-positive" />
                            )
                          }
                          className="hover:border-accent-primary text-xs w-full sm:w-auto"
                        >
                          {isAcknowledging ? 'Acknowledging...' : 'Acknowledge'}
                        </Button>
                      )}

                      {alert.status === 'ACKNOWLEDGED' && (
                        <div className="flex items-center gap-1.5 text-xs text-status-info bg-status-info-soft border border-status-info/40 font-medium px-3 py-1.5 rounded-lg shadow-xs">
                          <CheckCheck className="w-3.5 h-3.5 text-status-info shrink-0" />
                          <span>
                            Acknowledged
                            {alert.acknowledged_at && (
                              <span className="text-text-muted ml-1 text-[11px] font-normal">
                                {formatDate(alert.acknowledged_at, { format: 'relative' })}
                              </span>
                            )}
                          </span>
                        </div>
                      )}

                      {alert.status === 'RESOLVED' && (
                        <div className="flex items-center gap-1.5 text-xs text-status-positive bg-status-positive-soft border border-status-positive/40 font-medium px-3 py-1.5 rounded-lg shadow-xs">
                          <CheckCircle2 className="w-3.5 h-3.5 text-status-positive shrink-0" />
                          <span>Condition Normalized</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
};
