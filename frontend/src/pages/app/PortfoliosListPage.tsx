import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { CreatePortfolioModal } from '../../components/portfolio/CreatePortfolioModal';
import { DeleteConfirmModal } from '../../components/portfolio/DeleteConfirmModal';
import { portfolioApi } from '../../api/portfolio';
import {
  Portfolio,
  CreatePortfolioPayload,
  getPortfolioCurrentValue,
  getPortfolioInvestedValue,
  getPortfolioPnL,
  getPortfolioPnLPercent,
} from '../../types/portfolio';
import { formatCurrency, formatPercent, formatDate } from '../../utils/formatters';
import {
  Plus,
  Briefcase,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Bot,
  Search,
  RefreshCw,
  Trash2,
  PieChart,
} from 'lucide-react';

export const PortfoliosListPage: React.FC = () => {
  const navigate = useNavigate();

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingPortfolio, setDeletingPortfolio] = useState<Portfolio | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchPortfolios = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await portfolioApi.getPortfolios();
      setPortfolios(data);
    } catch (err: any) {
      console.error('Failed to load portfolios:', err);
      setError(err?.message || 'Failed to fetch portfolios. Please check your backend connection.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  // Filtered portfolios
  const filteredPortfolios = portfolios.filter((p) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return (
      p.name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });

  const handleCreatePortfolio = async (payload: CreatePortfolioPayload) => {
    setIsSubmitting(true);
    try {
      const created = await portfolioApi.createPortfolio(payload);
      setPortfolios((prev) => [created, ...prev]);
      navigate(`/app/portfolio/${created.id}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeletePortfolio = async () => {
    if (!deletingPortfolio) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await portfolioApi.deletePortfolio(deletingPortfolio.id);
      setPortfolios((prev) => prev.filter((p) => p.id !== deletingPortfolio.id));
      setDeletingPortfolio(null);
    } catch (err: any) {
      console.error('Failed to delete portfolio:', err);
      setDeleteError(err?.message || 'Failed to delete portfolio. Permission denied or resource unavailable.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Portfolio Management"
        subtitle="Active investment mandates, holdings registers, and real-time backend valuations"
        badge={
          <Badge variant="info" size="sm" dot>
            Phase C Active
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchPortfolios}
              disabled={isLoading}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Create Portfolio
            </Button>
          </div>
        }
      />

      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 p-3 sm:p-4 rounded-xl">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search portfolios by name or mandate..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/80 text-slate-200 placeholder:text-slate-500 text-xs rounded-lg border border-slate-700/80 pl-9 pr-3 py-2 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Showing {filteredPortfolios.length} of {portfolios.length} portfolios
        </div>
      </div>

      {/* Error state */}
      {error && (
        <ErrorState
          title="Could not load portfolios"
          message={error}
          onRetry={fetchPortfolios}
        />
      )}

      {/* Loading Skeleton */}
      {isLoading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <LoadingSkeleton height="h-5" width="w-36" />
                <LoadingSkeleton height="h-4" width="w-12" />
              </div>
              <LoadingSkeleton height="h-3" width="w-full" />
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-800/60">
                <LoadingSkeleton height="h-10" width="w-full" />
                <LoadingSkeleton height="h-10" width="w-full" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && portfolios.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No investment portfolios yet"
          description="Create your first portfolio to record asset holdings, track live valuations, and run AI multi-agent diagnostics."
          actionLabel="Create First Portfolio"
          onAction={() => setIsCreateModalOpen(true)}
          className="my-10 p-12"
        />
      )}

      {/* Filtered Empty State */}
      {!isLoading && !error && portfolios.length > 0 && filteredPortfolios.length === 0 && (
        <div className="text-center py-12 bg-slate-900/40 border border-dashed border-slate-800 rounded-xl">
          <p className="text-sm text-slate-400">
            No portfolios match "{searchQuery}".
          </p>
        </div>
      )}

      {/* Portfolio Cards Grid */}
      {!isLoading && !error && filteredPortfolios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredPortfolios.map((p) => {
            const currency = p.currency || 'INR';
            const currVal = getPortfolioCurrentValue(p);
            const investedVal = getPortfolioInvestedValue(p);
            const pnl = getPortfolioPnL(p);
            const pnlPct = getPortfolioPnLPercent(p);
            const count = p.holdings_count ?? p.total_holdings ?? p.holdings?.length ?? 0;
            const isGain = pnl !== null ? pnl >= 0 : null;

            return (
              <div
                key={p.id}
                className="bg-slate-900/70 hover:bg-slate-900 border border-slate-800/90 hover:border-slate-700/80 rounded-xl p-5 transition-all shadow-sm flex flex-col justify-between group"
              >
                {/* Header */}
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3
                        onClick={() => navigate(`/app/portfolio/${p.id}`)}
                        className="text-base font-semibold text-slate-100 group-hover:text-cyan-400 transition-colors cursor-pointer truncate"
                      >
                        {p.name}
                      </h3>
                      {p.description && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                          {p.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant="neutral" size="sm">
                        {currency}
                      </Badge>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingPortfolio(p);
                        }}
                        className="p-1 text-slate-400 hover:text-rose-400 rounded-md hover:bg-rose-500/10 transition-colors"
                        title="Delete portfolio"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Financial Metrics Strip */}
                  <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-800/80">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                        Current Value
                      </span>
                      <span className="text-sm font-bold font-mono text-slate-100 mt-0.5 block">
                        {currVal !== null ? formatCurrency(currVal, currency) : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                        Invested
                      </span>
                      <span className="text-sm font-mono text-slate-300 mt-0.5 block">
                        {investedVal !== null ? formatCurrency(investedVal, currency) : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                        Profit / Loss
                      </span>
                      <span
                        className={`text-xs font-semibold font-mono flex items-center gap-0.5 mt-0.5 ${
                          isGain === null
                            ? 'text-slate-400'
                            : isGain
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {isGain !== null && (isGain ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />)}
                        {pnl !== null ? formatCurrency(pnl, currency) : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                        Return (%)
                      </span>
                      <span
                        className={`text-xs font-semibold font-mono mt-0.5 block ${
                          isGain === null
                            ? 'text-slate-400'
                            : isGain
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {pnlPct !== null ? formatPercent(pnlPct, true) : '—'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span>{count} {count === 1 ? 'position' : 'positions'}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => navigate(`/app/portfolio/${p.id}`)}
                    >
                      Open Detail
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Portfolio Modal */}
      <CreatePortfolioModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreatePortfolio}
        isLoading={isSubmitting}
      />

      {/* Delete Portfolio Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={Boolean(deletingPortfolio)}
        onClose={() => {
          setDeletingPortfolio(null);
          setDeleteError(null);
        }}
        onConfirm={handleDeletePortfolio}
        title="Delete Portfolio"
        message={`Are you sure you want to delete "${deletingPortfolio?.name}"? All associated asset holdings and records will be removed.`}
        confirmLabel="Delete Portfolio"
        isLoading={isDeleting}
        error={deleteError}
      />
    </div>
  );
};
