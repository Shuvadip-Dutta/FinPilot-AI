/**
 * FinPilot-AI Module 15: Alerts and Monitoring TypeScript Contracts
 * Matches authoritative Django REST Framework serializers and viewsets.
 */

export type AlertType = 'concentration_breach' | 'drawdown_breach' | 'loss_threshold';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';

export interface Alert {
  id: string;
  portfolio: string;
  user: number | string;
  alert_type: AlertType | string;
  severity: AlertSeverity | string;
  status: AlertStatus | string;
  title: string;
  message: string;
  metric_value: string | number;
  threshold_value: string | number;
  acknowledged_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MonitoringEventSummary {
  alert_type: string;
  severity?: string;
  title: string;
  message?: string;
  metric_value: string | number;
  threshold_value: string | number;
  metadata?: Record<string, any>;
  reason?: string;
}

export interface MonitoringResponse {
  portfolio_id: string;
  evaluated_at: string;
  events: MonitoringEventSummary[];
  detected_events: MonitoringEventSummary[];
  alerts_created: Alert[];
  alerts_suppressed: MonitoringEventSummary[];
}

export interface RunMonitoringPayload {
  to_date?: string;
  from_date?: string;
  last_prices?: Record<string, number>;
}
