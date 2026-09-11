/**
 * Financial and general data formatting utilities for FinPilot AI
 */

export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = 'INR',
  options?: { compact?: boolean }
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  const symbol = currency === 'INR' ? '₹' : currency === 'USD' ? '$' : `${currency} `;

  // Compact Indian numbering notation for large figures (Crores, Lakhs) if requested
  if (options?.compact && currency === 'INR') {
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';
    if (abs >= 10000000) {
      return `${sign}${symbol}${(abs / 10000000).toFixed(2)} Cr`;
    }
    if (abs >= 100000) {
      return `${sign}${symbol}${(abs / 100000).toFixed(2)} L`;
    }
  }

  // Standard locale formatting
  const formatted = Math.abs(num).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return `${num < 0 ? '-' : ''}${symbol}${formatted}`;
}

export function formatPercent(
  value: number | string | null | undefined,
  includeSign: boolean = true,
  decimals: number = 2
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  const sign = includeSign && num > 0 ? '+' : '';
  return `${sign}${num.toFixed(decimals)}%`;
}

export function formatNumber(
  value: number | string | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  return num.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatRatio(
  value: number | string | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  return num.toFixed(decimals);
}

export function formatDate(
  dateString: string | number | Date | null | undefined,
  options?: { includeTime?: boolean; format?: 'short' | 'medium' | 'relative' }
): string {
  if (!dateString) return '—';

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '—';

    if (options?.format === 'relative') {
      const diffMs = Date.now() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
    }

    if (options?.includeTime) {
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}
