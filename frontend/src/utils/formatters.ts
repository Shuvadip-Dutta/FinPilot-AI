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

/**
 * Context-aware financial statement metric formatter.
 * Ensures:
 * - Monetary figures (revenue, net profit, cash flow, debt, assets) use consistent compact currency
 * - Valuation and liquidity ratios (P/E, P/B, EV/EBITDA, Quick Ratio, Debt/Equity, Beta) are formatted as pure numbers/ratios, NOT currency
 * - Profitability and growth metrics (Margins, ROE, ROCE, ROA, Yield, Tax Rate) are formatted as percentages
 * - Per-share metrics (EPS, Diluted EPS) are formatted as per-share currency (e.g. ₹45.20)
 * - Negative values preserve negative sign and formatting
 */
export function formatFinancialStatementValue(
  name: string,
  key: string,
  value: number | string | null | undefined,
  currency: string = 'INR'
): string {
  if (value === null || value === undefined || value === '') return '—';
  const num =
    typeof value === 'string'
      ? parseFloat(value.replace(/,/g, '').trim())
      : typeof value === 'number'
      ? value
      : Number(value);
  if (isNaN(num)) return '—';

  const lowerName = (name || '').toLowerCase();
  const lowerKey = (key || '').toLowerCase();

  // 1. Check if percentage / margin / return / growth metric (e.g. EPS Growth, Revenue Growth, OPM, ROE)
  // Growth metrics take precedence over per-share labels to avoid classifying "EPS Growth" as currency EPS.
  if (
    lowerKey.includes('margin') ||
    lowerKey.includes('yield') ||
    lowerKey.includes('tax_rate') ||
    lowerKey.includes('growth') ||
    lowerKey.includes('cagr') ||
    lowerKey.includes('percentage') ||
    lowerKey.includes('pct') ||
    lowerKey.includes('roe') ||
    lowerKey.includes('roa') ||
    lowerKey.includes('roce') ||
    lowerName.includes('margin') ||
    lowerName.includes('yield') ||
    lowerName.includes('tax rate') ||
    lowerName.includes('growth') ||
    lowerName.includes('cagr') ||
    lowerName.includes('roe') ||
    lowerName.includes('roa') ||
    lowerName.includes('roce') ||
    lowerName.includes('return on') ||
    lowerName.includes('%')
  ) {
    return formatPercent(num, false, 2);
  }

  // 2. Check if per-share metric (Basic EPS, Diluted EPS, DPS, Cash EPS) - NOT growth
  if (
    lowerKey === 'eps' ||
    lowerKey === 'diluted_eps' ||
    lowerKey.includes('per_share') ||
    lowerName.includes('eps') ||
    lowerName.includes('per share')
  ) {
    return formatCurrency(num, currency);
  }

  // 3. Check if valuation / financial ratio (NOT currency!)
  // e.g. P/E, P/B, EV/EBITDA, EV / EBITDA, Quick Ratio, Debt to Equity, Current Ratio, Beta
  if (
    lowerKey.includes('ratio') ||
    lowerKey.includes('multiple') ||
    lowerKey.includes('pe_') ||
    lowerKey.includes('pb_') ||
    lowerKey.includes('ev_') ||
    lowerKey.includes('debt_to_equity') ||
    lowerKey === 'p_e' ||
    lowerKey === 'p_b' ||
    lowerKey === 'ev_ebitda' ||
    lowerKey === 'pe' ||
    lowerKey === 'pb' ||
    lowerKey === 'beta' ||
    lowerName.includes('ratio') ||
    lowerName.includes('multiple') ||
    lowerName.includes('p/e') ||
    lowerName.includes('p/b') ||
    lowerName.includes('ev/ebitda') ||
    lowerName.includes('ev / ebitda') ||
    lowerName.includes('beta') ||
    lowerName.includes('debt to equity')
  ) {
    return formatRatio(num, 2);
  }

  // 4. Check if share count / volume
  if (lowerKey.includes('shares') || lowerKey.includes('volume') || lowerName.includes('shares')) {
    return formatNumber(num, 0);
  }

  // 5. Default: Monetary line items (Revenue, Expenses, Profit, Cash Flow, Assets, Liabilities, Capex, Debt)
  if (currency === 'INR') {
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';
    const symbol = '₹';
    if (abs >= 10000000) {
      return `${sign}${symbol}${(abs / 10000000).toFixed(2)} Cr`;
    }
    // Financial statement compact Lakhs notation (e.g. 1086181 -> ₹10.86 L, 123162 -> ₹1.23 L, 95610 -> ₹0.96 L, 94046 -> ₹0.94 L)
    // Values >= 10,000 are displayed consistently in Lakhs to prevent row-to-row formatting jumps
    if (abs >= 10000) {
      return `${sign}${symbol}${(abs / 100000).toFixed(2)} L`;
    }
    if (abs >= 1000) {
      return `${sign}${symbol}${(abs / 1000).toFixed(2)} K`;
    }
    return formatCurrency(num, currency);
  }

  if (currency === 'USD') {
    const abs = Math.abs(num);
    const sign = num < 0 ? '-' : '';
    const symbol = '$';
    if (abs >= 1000000000) {
      return `${sign}${symbol}${(abs / 1000000000).toFixed(2)} B`;
    }
    if (abs >= 1000000) {
      return `${sign}${symbol}${(abs / 1000000).toFixed(2)} M`;
    }
    if (abs >= 1000) {
      return `${sign}${symbol}${(abs / 1000).toFixed(2)} K`;
    }
    return formatCurrency(num, currency);
  }

  return formatCurrency(num, currency, { compact: true });
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
