import React, { useState, useMemo } from 'react';
import {
  Holding,
  getHoldingInvestedValue,
  getHoldingCurrentValue,
  getHoldingCurrentPrice,
  getHoldingPnL,
  getHoldingPnLPercent,
  getHoldingAllocation,
} from '../../types/portfolio';
import { formatCurrency, formatPercent, formatNumber } from '../../utils/formatters';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { EmptyState } from '../common/EmptyState';
import {
  Search,
  Plus,
  Edit2,
  Trash2,
  ExternalLink,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface HoldingsTableProps {
  holdings: Holding[];
  currency?: string;
  onAddHolding: () => void;
  onEditHolding: (holding: Holding) => void;
  onDeleteHolding: (holding: Holding) => void;
  isLoading?: boolean;
}

export const HoldingsTable: React.FC<HoldingsTableProps> = ({
  holdings,
  currency = 'INR',
  onAddHolding,
  onEditHolding,
  onDeleteHolding,
  isLoading = false,
}) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMarket, setSelectedMarket] = useState<string>('ALL');

  // Calculate total portfolio invested capital to show presentation-only holding weight
  const totalPortfolioInvested = useMemo(() => {
    return holdings.reduce((sum, h) => {
      const inv = getHoldingInvestedValue(h);
      return sum + (inv ?? 0);
    }, 0);
  }, [holdings]);

  // Filtered holdings list
  const filteredHoldings = useMemo(() => {
    return holdings.filter((item) => {
      const ticker = (item.ticker || '').toUpperCase();
      const query = searchQuery.trim().toUpperCase();

      const matchesSearch = !query || ticker.includes(query);
      const matchesMarket =
        selectedMarket === 'ALL' || (item.market || 'IN').toUpperCase() === selectedMarket;

      return matchesSearch && matchesMarket;
    });
  }, [holdings, searchQuery, selectedMarket]);

  return (
    <div className="bg-slate-900/70 border border-slate-800/90 rounded-xl overflow-hidden shadow-sm">
      {/* Header controls */}
      <div className="p-4 sm:p-5 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-100">Holdings & Positions</h3>
            <Badge variant="neutral" size="sm">
              {holdings.length} {holdings.length === 1 ? 'asset' : 'assets'}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Persisted ledger securities and cost basis
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Search box */}
          <div className="relative min-w-[180px] sm:min-w-[220px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search ticker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/60 text-slate-200 placeholder:text-slate-500 text-xs rounded-lg border border-slate-700/80 pl-8 pr-3 py-1.5 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          {/* Market filter */}
          <select
            value={selectedMarket}
            onChange={(e) => setSelectedMarket(e.target.value)}
            className="bg-slate-950/60 text-slate-200 text-xs rounded-lg border border-slate-700/80 px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 transition-colors"
          >
            <option value="ALL">All Markets</option>
            <option value="IN">IN (India)</option>
            <option value="US">US (United States)</option>
          </select>

          {/* Add Holding CTA */}
          <Button
            variant="primary"
            size="sm"
            onClick={onAddHolding}
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Add Holding
          </Button>
        </div>
      </div>

      {/* Holdings list or empty states */}
      {holdings.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No holdings in this portfolio yet"
          description="Add your first stock or ETF position to record holdings and run AI portfolio analysis."
          actionLabel="Add Holding"
          onAction={onAddHolding}
          className="border-0 bg-transparent my-6"
        />
      ) : filteredHoldings.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-sm">
          No holdings match your search query "{searchQuery}".
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] font-semibold uppercase tracking-wider text-slate-400 select-none">
                <th className="py-3 px-4">Asset / Ticker</th>
                <th className="py-3 px-4 text-right">Quantity</th>
                <th className="py-3 px-4 text-right">Avg Buy Price</th>
                <th className="py-3 px-4 text-right">Invested Capital</th>
                <th className="py-3 px-4 text-right">Capital Weight</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {filteredHoldings.map((h) => {
                const ticker = h.ticker || 'UNKNOWN';
                const market = h.market || 'IN';
                const quantity = typeof h.quantity === 'string' ? parseFloat(h.quantity) : h.quantity;
                const buyPrice = typeof h.average_price === 'string' ? parseFloat(h.average_price) : h.average_price;
                const investedVal = getHoldingInvestedValue(h);
                const holdingWeight = (totalPortfolioInvested > 0 && investedVal !== null)
                  ? (investedVal / totalPortfolioInvested) * 100
                  : null;

                const holdingCurrency = market === 'US' ? 'USD' : 'INR';

                return (
                  <tr
                    key={h.id}
                    className="hover:bg-slate-800/30 transition-colors group"
                  >
                    {/* Ticker & Market */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-100 text-sm">
                          {ticker}
                        </span>
                        <Badge variant="neutral" size="sm">
                          {market}
                        </Badge>
                      </div>
                    </td>

                    {/* Quantity */}
                    <td className="py-3.5 px-4 text-right font-mono text-slate-200">
                      {formatNumber(quantity, 4)}
                    </td>

                    {/* Avg Buy Price */}
                    <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                      {formatCurrency(buyPrice, holdingCurrency)}
                    </td>

                    {/* Invested Value */}
                    <td className="py-3.5 px-4 text-right font-mono text-slate-100 font-semibold">
                      {investedVal !== null ? formatCurrency(investedVal, holdingCurrency) : '—'}
                    </td>

                    {/* Capital Weight */}
                    <td className="py-3.5 px-4 text-right font-mono text-cyan-400 font-medium">
                      {holdingWeight !== null ? formatPercent(holdingWeight, false) : '—'}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {/* Quick AI Research Linkout */}
                        <button
                          type="button"
                          onClick={() => navigate(`/app/research?ticker=${ticker}&market=${market}`)}
                          className="p-1 text-slate-400 hover:text-cyan-400 rounded-md hover:bg-slate-800/80 transition-colors"
                          title={`Research ${ticker} with FinPilot AI`}
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>

                        {/* Edit Holding */}
                        <button
                          type="button"
                          onClick={() => onEditHolding(h)}
                          className="p-1 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-800/80 transition-colors"
                          title="Edit holding"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>

                        {/* Delete Holding */}
                        <button
                          type="button"
                          onClick={() => onDeleteHolding(h)}
                          className="p-1 text-slate-400 hover:text-rose-400 rounded-md hover:bg-rose-500/10 transition-colors"
                          title="Delete holding"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
