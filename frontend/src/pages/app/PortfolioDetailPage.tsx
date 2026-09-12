import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { ErrorState } from '../../components/common/ErrorState';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { PortfolioSummaryCard } from '../../components/portfolio/PortfolioSummaryCard';
import { AllocationChart } from '../../components/portfolio/AllocationChart';
import { HoldingsTable } from '../../components/portfolio/HoldingsTable';
import { HoldingModal } from '../../components/portfolio/HoldingModal';
import { EditPortfolioModal } from '../../components/portfolio/EditPortfolioModal';
import { DeleteConfirmModal } from '../../components/portfolio/DeleteConfirmModal';
import { PortfolioAiAnalysisModal } from '../../components/portfolio/PortfolioAiAnalysisModal';
import { portfolioApi } from '../../api/portfolio';
import {
  Portfolio,
  Holding,
  CreateHoldingPayload,
  UpdateHoldingPayload,
  UpdatePortfolioPayload,
} from '../../types/portfolio';
import {
  ArrowLeft,
  Plus,
  Bot,
  Edit2,
  Trash2,
  RefreshCw,
  Clock,
  ShieldAlert,
  Sliders,
  GitFork,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

export const PortfolioDetailPage: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [aiValuation, setAiValuation] = useState<any | null>(null);

  // Modals state
  const [isAddHoldingOpen, setIsAddHoldingOpen] = useState<boolean>(false);
  const [editingHolding, setEditingHolding] = useState<Holding | null>(null);
  const [deletingHolding, setDeletingHolding] = useState<Holding | null>(null);
  const [isEditPortfolioOpen, setIsEditPortfolioOpen] = useState<boolean>(false);
  const [isDeletePortfolioOpen, setIsDeletePortfolioOpen] = useState<boolean>(false);
  const [isAiAnalysisOpen, setIsAiAnalysisOpen] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [portfolioDeleteError, setPortfolioDeleteError] = useState<string | null>(null);
  const [holdingDeleteError, setHoldingDeleteError] = useState<string | null>(null);

  // Fetch portfolio details and holdings list
  const loadPortfolioData = useCallback(async () => {
    if (!portfolioId) return;
    setIsLoading(true);
    setError(null);

    try {
      // Parallel fetch of portfolio valuation and holdings
      const [portfolioRes, holdingsRes] = await Promise.all([
        portfolioApi.getPortfolio(portfolioId),
        portfolioApi.getHoldings(portfolioId),
      ]);

      setPortfolio(portfolioRes);
      setHoldings(holdingsRes);
    } catch (err: any) {
      console.error('Failed to load portfolio detail:', err);
      setError(err?.response?.data?.error || err?.message || 'Failed to retrieve portfolio. Please verify backend state.');
    } finally {
      setIsLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    loadPortfolioData();
  }, [loadPortfolioData]);

  // Update Portfolio
  const handleUpdatePortfolio = async (payload: UpdatePortfolioPayload) => {
    if (!portfolioId) return;
    setIsActionLoading(true);
    try {
      const updated = await portfolioApi.updatePortfolio(portfolioId, payload);
      setPortfolio(updated);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Delete Portfolio
  const handleDeletePortfolio = async () => {
    if (!portfolioId) return;
    setIsActionLoading(true);
    setPortfolioDeleteError(null);
    try {
      await portfolioApi.deletePortfolio(portfolioId);
      navigate('/app/portfolio');
    } catch (err: any) {
      console.error('Failed to delete portfolio:', err);
      setPortfolioDeleteError(err?.response?.data?.error || err?.message || 'Failed to delete portfolio. Permission denied or resource unavailable.');
    } finally {
      setIsActionLoading(false);
    }
  };

  // Add Holding - mutation clears previous AI live valuation
  const handleAddHolding = async (payload: CreateHoldingPayload) => {
    if (!portfolioId) return;
    setIsActionLoading(true);
    try {
      await portfolioApi.addHolding(portfolioId, payload);
      setAiValuation(null); // Clear stale AI valuation after mutation
      await loadPortfolioData();
    } finally {
      setIsActionLoading(false);
    }
  };

  // Edit Holding - mutation clears previous AI live valuation
  const handleEditHolding = async (payload: UpdateHoldingPayload) => {
    if (!portfolioId || !editingHolding) return;
    setIsActionLoading(true);
    try {
      await portfolioApi.updateHolding(portfolioId, editingHolding.id, payload);
      setEditingHolding(null);
      setAiValuation(null); // Clear stale AI valuation after mutation
      await loadPortfolioData();
    } finally {
      setIsActionLoading(false);
    }
  };

  // Delete Holding - mutation clears previous AI live valuation
  const handleDeleteHolding = async () => {
    if (!portfolioId || !deletingHolding) return;
    setIsActionLoading(true);
    setHoldingDeleteError(null);
    try {
      await portfolioApi.deleteHolding(portfolioId, deletingHolding.id);
      setDeletingHolding(null);
      setAiValuation(null); // Clear stale AI valuation after mutation
      await loadPortfolioData();
    } catch (err: any) {
      console.error('Failed to delete holding:', err);
      setHoldingDeleteError(err?.response?.data?.error || err?.message || 'Failed to delete holding position.');
    } finally {
      setIsActionLoading(false);
    }
  };

  if (isLoading && !portfolio) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <LoadingSkeleton height="h-8" width="w-8" />
          <LoadingSkeleton height="h-8" width="w-48" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <LoadingSkeleton key={i} height="h-24" width="w-full" />
          ))}
        </div>
        <LoadingSkeleton height="h-64" width="w-full" />
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <ErrorState
        title="Portfolio unavailable"
        message={error || 'Unable to find the requested portfolio.'}
        onRetry={loadPortfolioData}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/app/portfolio')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-md hover:bg-slate-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Portfolios</span>
        </button>
      </div>

      {/* Page Header with Actions */}
      <PageHeader
        title={
          <div className="flex items-center gap-3 flex-wrap">
            <span>{portfolio.name}</span>
            <Badge variant="neutral" size="sm">
              INR
            </Badge>
          </div>
        }
        subtitle={
          <div className="flex items-center gap-3 flex-wrap">
            <span>Quantitative Asset Ledger & Portfolio Intelligence</span>
            {portfolio.updated_at && (
              <span className="flex items-center gap-1 text-[11px] text-slate-500">
                <Clock className="w-3 h-3" />
                Updated {formatDate(portfolio.updated_at, { format: 'relative' })}
              </span>
            )}
          </div>
        }
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {/* AI Portfolio Audit Entry Point */}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsAiAnalysisOpen(true)}
              className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
              leftIcon={<Bot className="w-4 h-4 text-cyan-400" />}
            >
              AI Audit
            </Button>

            {/* Quantitative Risk Analysis (Phase D) */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/app/portfolio/${portfolioId}/risk`)}
              className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10"
              leftIcon={<ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />}
            >
              Risk Profile
            </Button>

            {/* Portfolio Optimization (Phase D) */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/app/portfolio/${portfolioId}/optimization`)}
              className="border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10"
              leftIcon={<Sliders className="w-3.5 h-3.5 text-emerald-400" />}
            >
              Optimize
            </Button>

            {/* Walk-Forward Backtest (Phase E) */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/app/portfolio/${portfolioId}/backtest`)}
              className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
              leftIcon={<GitFork className="w-3.5 h-3.5 text-indigo-400" />}
            >
              Backtest
            </Button>

            {/* Refresh */}
            <Button
              variant="outline"
              size="sm"
              onClick={loadPortfolioData}
              disabled={isLoading}
              title="Refresh valuations"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>

            {/* Add Holding */}
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsAddHoldingOpen(true)}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Holding
            </Button>

            {/* Edit Portfolio Settings */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditPortfolioOpen(true)}
              title="Edit portfolio properties"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </Button>

            {/* Delete Portfolio */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsDeletePortfolioOpen(true)}
              className="hover:text-rose-400"
              title="Delete portfolio"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        }
      />

      {/* Primary Financial Valuation Metrics */}
      <PortfolioSummaryCard
        portfolio={portfolio}
        holdingsCount={holdings.length}
        aiValuation={aiValuation}
      />

      {/* Asset Allocation Breakdown (Pie chart / distribution) */}
      <AllocationChart
        portfolio={portfolio}
        holdings={holdings}
      />

      {/* Positions / Holdings Table */}
      <HoldingsTable
        holdings={holdings}
        currency="INR"
        onAddHolding={() => setIsAddHoldingOpen(true)}
        onEditHolding={(holding) => setEditingHolding(holding)}
        onDeleteHolding={(holding) => setDeletingHolding(holding)}
        isLoading={isLoading}
      />

      {/* Add Holding Modal */}
      <HoldingModal
        isOpen={isAddHoldingOpen}
        onClose={() => setIsAddHoldingOpen(false)}
        currency="INR"
        onSubmit={handleAddHolding}
        isLoading={isActionLoading}
      />

      {/* Edit Holding Modal */}
      <HoldingModal
        isOpen={Boolean(editingHolding)}
        onClose={() => setEditingHolding(null)}
        holding={editingHolding}
        currency="INR"
        onSubmit={handleEditHolding}
        isLoading={isActionLoading}
      />

      {/* Delete Holding Confirmation */}
      <DeleteConfirmModal
        isOpen={Boolean(deletingHolding)}
        onClose={() => {
          setDeletingHolding(null);
          setHoldingDeleteError(null);
        }}
        onConfirm={handleDeleteHolding}
        title="Delete Holding"
        message={`Are you sure you want to remove ${deletingHolding?.ticker} from this portfolio?`}
        confirmLabel="Remove Position"
        isLoading={isActionLoading}
        error={holdingDeleteError}
      />

      {/* Edit Portfolio Modal */}
      <EditPortfolioModal
        isOpen={isEditPortfolioOpen}
        onClose={() => setIsEditPortfolioOpen(false)}
        portfolio={portfolio}
        onSubmit={handleUpdatePortfolio}
        isLoading={isActionLoading}
      />

      {/* Delete Portfolio Modal */}
      <DeleteConfirmModal
        isOpen={isDeletePortfolioOpen}
        onClose={() => {
          setIsDeletePortfolioOpen(false);
          setPortfolioDeleteError(null);
        }}
        onConfirm={handleDeletePortfolio}
        title="Delete Portfolio"
        message={`Permanently delete "${portfolio.name}" and all ${holdings.length} associated holdings? This action cannot be undone.`}
        confirmLabel="Delete Portfolio"
        isLoading={isActionLoading}
        error={portfolioDeleteError}
      />

      {/* AI Analysis Modal (Portfolio AI Analysis Entry Point) */}
      <PortfolioAiAnalysisModal
        isOpen={isAiAnalysisOpen}
        onClose={() => setIsAiAnalysisOpen(false)}
        portfolio={portfolio}
        holdings={holdings}
        onAnalysisSuccess={(structured) => setAiValuation(structured)}
      />
    </div>
  );
};
