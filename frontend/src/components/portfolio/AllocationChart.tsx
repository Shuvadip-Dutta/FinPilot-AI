import React from 'react';
import {
  Portfolio,
  Holding,
  AllocationItem,
  getHoldingAllocation,
  getHoldingCurrentValue,
} from '../../types/portfolio';
import { formatPercent, formatCurrency } from '../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';

export interface AllocationChartProps {
  portfolio: Portfolio | null;
  holdings: Holding[];
  className?: string;
}

const PALETTE = [
  '#06b6d4', // cyan-500
  '#6366f1', // indigo-500
  '#8b5cf6', // violet-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#0ea5e9', // sky-500
  '#ec4899', // pink-500
  '#14b8a6', // teal-500
  '#64748b', // slate-500
];

export const AllocationChart: React.FC<AllocationChartProps> = ({
  portfolio,
  holdings,
  className = '',
}) => {
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
      color: PALETTE[idx % PALETTE.length],
    }));
  }, [holdings]);

  if (allocationItems.length === 0) {
    return (
      <div className={`bg-slate-900/60 border border-slate-800/90 rounded-xl p-6 ${className}`}>
        <div className="flex items-center gap-2 mb-3">
          <PieChartIcon className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">Current Asset Allocation</h3>
        </div>
        <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-lg p-4">
          Allocation weights will be displayed when backend portfolio metrics are returned.
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-slate-900/60 border border-slate-800/90 rounded-xl p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <PieChartIcon className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">Current Asset Allocation</h3>
        </div>
        <span className="text-xs text-slate-400 font-mono">
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
                stroke="#0f172a"
                strokeWidth={2}
              >
                {allocationItems.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color || PALETTE[index % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  fontFamily: 'monospace',
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
              className="flex items-center justify-between p-2 rounded-lg bg-slate-950/40 border border-slate-800/60 text-xs"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color || PALETTE[idx % PALETTE.length] }}
                />
                <span className="font-semibold text-slate-200 font-mono truncate">{item.name}</span>
                {item.value !== null && item.value !== undefined && (
                  <span className="text-slate-500 font-mono hidden sm:inline">
                    · {formatCurrency(item.value, currency)}
                  </span>
                )}
              </div>
              <div className="font-mono font-semibold text-cyan-400 shrink-0 ml-3">
                {formatPercent(item.percentage, false)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
