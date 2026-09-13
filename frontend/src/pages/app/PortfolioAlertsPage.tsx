import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { AlertCenter } from '../../components/portfolio/AlertCenter';
import { portfolioApi } from '../../api/portfolio';
import { Portfolio } from '../../types/portfolio';
import {
  ArrowLeft,
  Briefcase,
  ChevronDown,
  PieChart,
  Plus,
  ShieldAlert,
} from 'lucide-react';

export const PortfolioAlertsPage: React.FC = () => {
  const { portfolioId: paramPortfolioId } = useParams<{ portfolioId?: string }>();
  const navigate = useNavigate();

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(
    paramPortfolioId || null
  );
  const [currentPortfolio, setCurrentPortfolio] = useState<Portfolio | null>(null);
  const [isLoadingPortfolios, setIsLoadingPortfolios] = useState<boolean>(true);

  // Load portfolios list
  useEffect(() => {
    const fetchPortfolios = async () => {
      setIsLoadingPortfolios(true);
      try {
        const list = await portfolioApi.getPortfolios();
        setPortfolios(list);

        if (paramPortfolioId) {
          const match = list.find((p) => String(p.id) === String(paramPortfolioId));
          if (match) {
            setSelectedPortfolioId(match.id);
            setCurrentPortfolio(match);
          } else if (list.length > 0) {
            setSelectedPortfolioId(list[0].id);
            setCurrentPortfolio(list[0]);
          }
        } else if (list.length > 0) {
          setSelectedPortfolioId(list[0].id);
          setCurrentPortfolio(list[0]);
        }
      } catch (err) {
        console.error('Failed to load portfolios for alerts page:', err);
      } finally {
        setIsLoadingPortfolios(false);
      }
    };

    fetchPortfolios();
  }, [paramPortfolioId]);

  // Handle switching portfolio via selector
  const handleSelectPortfolio = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const nextId = e.target.value;
    setSelectedPortfolioId(nextId);
    const match = portfolios.find((p) => String(p.id) === String(nextId));
    if (match) {
      setCurrentPortfolio(match);
      navigate(`/app/portfolio/${nextId}/alerts`);
    }
  };

  if (isLoadingPortfolios) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <LoadingSkeleton height="h-8" width="w-48" />
        </div>
        <LoadingSkeleton height="h-64" width="w-full" className="rounded-xl" />
      </div>
    );
  }

  if (portfolios.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Portfolio Alert Center"
          subtitle="Real-time quantitative risk condition monitoring"
        />
        <EmptyState
          icon={PieChart}
          title="No Portfolios Found"
          description="Create a portfolio and add positions to enable automated risk monitoring and alerts."
          actionLabel="Create Portfolio"
          onAction={() => navigate('/app/portfolio')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <button
          type="button"
          onClick={() =>
            selectedPortfolioId
              ? navigate(`/app/portfolio/${selectedPortfolioId}`)
              : navigate('/app/portfolio')
          }
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-md hover:bg-slate-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>
            {currentPortfolio ? `Back to ${currentPortfolio.name}` : 'Back to Portfolios'}
          </span>
        </button>

        {/* Portfolio Selector */}
        {portfolios.length > 1 && (
          <div className="relative inline-flex items-center">
            <Briefcase className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
            <select
              value={selectedPortfolioId || ''}
              onChange={handleSelectPortfolio}
              aria-label="Select portfolio"
              className="bg-slate-900 border border-slate-700/80 text-slate-200 text-xs rounded-lg pl-8 pr-8 py-1.5 focus:outline-hidden focus:ring-1 focus:ring-cyan-500 appearance-none font-medium cursor-pointer hover:border-slate-600 transition-colors"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" />
          </div>
        )}
      </div>

      {/* Page Header */}
      <PageHeader
        title={
          <div className="flex items-center gap-2.5 flex-wrap">
            <span>{currentPortfolio?.name || 'Portfolio'} Alert Center</span>
          </div>
        }
        subtitle="Automated condition breach evaluation, cooldown tracking, and deterministic risk alerts"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}`)}
              leftIcon={<PieChart className="w-3.5 h-3.5" />}
            >
              View Holdings
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/app/portfolio/${selectedPortfolioId}/risk`)}
              leftIcon={<ShieldAlert className="w-3.5 h-3.5" />}
            >
              Risk Profile
            </Button>
          </div>
        }
      />

      {/* Alert Center Component */}
      {selectedPortfolioId && <AlertCenter portfolioId={selectedPortfolioId} />}
    </div>
  );
};
