import React from 'react';
import {
  Portfolio,
  Holding,
  AllocationItem,
} from '../../types/portfolio';
import { formatPercent, formatCurrency } from '../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import { useChartTheme } from '../../hooks/useChartTheme';

export interface AllocationChartProps {
  portfolio: Portfolio | null;
  holdings: Holding[];
  className?: string;
}

export const AllocationChart: React.FC<AllocationChartProps> = ({
  holdings,
  className = '',
}) => {
  const chartTheme = useChartTheme();
  const currency = 'INR';

  // Compute allocation breakdown strictly from holding invested value: quantity * average_price
  const allocationItems: AllocationItem[] = React.useMemo(() => {
    let totalInvested = 0;
    const items = holdings.map((h) => {
      const qty = typeof h.quantity === 'string' ? parseFloat(h.quantity) : h.quantity;
      const price = typeof h.average_price === 'string' ? parseFloat(h.average_price) : h.average_price;
      const inv = (qty && price && !isNaN(qty) && !isNaN(price)) ? qty * price : 0;
      totalInvested += inv;
      return {
        ticker: h.ticker,
        market: h.market,
        invested: inv,
      };
    });

    if (totalInvested <= 0) return [];

    return items.map((item, idx) => ({
      name: `${item.ticker} (${item.market})`,
      ticker: item.ticker,
      percentage: (item.invested / totalInvested) * 100,
      value: item.invested,
      color: chartTheme.allocationPalette[idx % chartTheme.allocationPalette.length],
    }));
  }, [holdings, chartTheme.allocationPalette]);

  if (allocationItems.length === 0) {
    return (
      <div className={`bg-surface border border-border-theme rounded-xl p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-3">
          <PieChartIcon className="w-4 h-4 text-accent-primary" />
          <h3 className="text-sm font-semibold text-text-primary">Current Asset Allocation</h3>
        </div>
        <div className="py-8 text-center text-xs text-text-muted border border-dashed border-border-theme rounded-lg p-4">
          Allocation weights will be displayed when backend portfolio metrics are returned.
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-surface border border-border-theme rounded-xl p-6 shadow-card ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <PieChartIcon className="w-4 h-4 text-accent-primary" />
          <h3 className="text-sm font-semibold text-text-primary">Current Asset Allocation</h3>
        </div>
        <span className="text-xs text-text-muted font-mono">
          {allocationItems.length} {allocationItems.length === 1 ? 'asset' : 'assets'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        {/* Donut Chart */}
        <div className="md:col-span-5 h-52 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={allocationItems}
                dataKey="percentage"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                stroke={chartTheme.tooltipBg}
                strokeWidth={2}
              >
                {allocationItems.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color || chartTheme.allocationPalette[index % chartTheme.allocationPalette.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: chartTheme.tooltipBg,
                  borderColor: chartTheme.tooltipBorder,
                  borderRadius: '0.75rem',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  color: chartTheme.text,
                  boxShadow: chartTheme.tooltipShadow,
                }}
                formatter={(value: any, name: any) => [
                  `${formatPercent(Number(value), false)}`,
                  String(name),
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend / Breakdown Table */}
        <div className="md:col-span-7 space-y-2.5 max-h-56 overflow-y-auto pr-1">
          {allocationItems.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2 rounded-lg bg-surface-secondary/70 border border-border-theme text-xs"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color || chartTheme.allocationPalette[idx % chartTheme.allocationPalette.length] }}
                />
                <span className="font-semibold text-text-primary font-mono truncate">{item.name}</span>
                {item.value !== null && item.value !== undefined && (
                  <span className="text-text-muted font-mono hidden sm:inline">
                    · {formatCurrency(item.value, currency)}
                  </span>
                )}
              </div>
              <div className="font-mono font-semibold text-accent-primary shrink-0 ml-3">
                {formatPercent(item.percentage, false)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
