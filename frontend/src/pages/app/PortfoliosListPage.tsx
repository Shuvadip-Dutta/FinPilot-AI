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
      setPortfolios(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error('Failed to load portfolios:', err);
      setError(err?.response?.data?.error || err?.message || 'Failed to fetch portfolios. Please check your backend connection.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  // Filtered portfolios by name
  const filteredPortfolios = portfolios.filter((p) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return p.name.toLowerCase().includes(q);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface border border-border-theme p-3 sm:p-4 rounded-xl">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search portfolios by name or mandate..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-secondary text-text-primary placeholder:text-text-muted text-xs rounded-lg border border-border-theme pl-9 pr-3 py-2 focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 transition-colors"
          />
        </div>
        <div className="text-xs text-text-muted font-mono">
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
            <div key={i} className="bg-surface border border-border-theme rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <LoadingSkeleton height="h-5" width="w-36" />
                <LoadingSkeleton height="h-4" width="w-12" />
              </div>
              <LoadingSkeleton height="h-3" width="w-full" />
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border-subtle">
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
        <div className="text-center py-12 bg-surface-secondary/40 border border-dashed border-border-theme rounded-xl">
          <p className="text-sm text-text-muted">
            No portfolios match "{searchQuery}".
          </p>
        </div>
      )}

      {/* Portfolio Cards Grid */}
      {!isLoading && !error && filteredPortfolios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredPortfolios.map((p) => {
            const investedVal = getPortfolioInvestedValue(p);
            const count = p.holdings?.length ?? 0;

            return (
              <div
                key={p.id}
                className="bg-surface hover:bg-surface-secondary/30 border border-border-theme hover:border-accent-primary/40 rounded-xl p-5 transition-all shadow-card flex flex-col justify-between group"
              >
                {/* Header */}
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3
                        onClick={() => navigate(`/app/portfolio/${p.id}`)}
                        className="text-base font-semibold text-text-primary group-hover:text-accent-primary transition-colors cursor-pointer truncate"
                      >
                        {p.name}
                      </h3>
                      <p className="text-[11px] text-text-muted font-mono mt-0.5">
                        ID: {p.id.slice(0, 8)}...
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant="neutral" size="sm">
                        INR
                      </Badge>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingPortfolio(p);
                        }}
                        className="p-1 text-text-muted hover:text-status-negative rounded-md hover:bg-status-negative-soft transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-negative cursor-pointer"
                        title="Delete portfolio"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Financial Metrics Strip */}
                  <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-border-subtle">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted block">
                        Invested Capital
                      </span>
                      <span className="text-sm font-bold font-mono text-text-primary mt-0.5 block">
                        {investedVal !== null ? formatCurrency(investedVal, 'INR') : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted block">
                        Holdings
                      </span>
                      <span className="text-sm font-mono text-text-secondary mt-0.5 block">
                        {count} {count === 1 ? 'position' : 'positions'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="mt-5 pt-4 border-t border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Layers className="w-3.5 h-3.5 text-text-muted" />
                    <span>{count} assets</span>
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
