import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/layout/PageHeader';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { ErrorState } from '../../components/common/ErrorState';
import { LoadingSkeleton } from '../../components/common/LoadingSkeleton';
import { MarkdownContent } from '../../components/research/MarkdownContent';
import { portfolioApi } from '../../api/portfolio';
import { researchApi } from '../../api/research';
import {
  Portfolio,
  Holding,
  getPortfolioCurrentValue,
  getPortfolioInvestedValue,
  getPortfolioPnL,
} from '../../types/portfolio';
import {
  ArrowLeft,
  Bot,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  Layers,
  ExternalLink,
} from 'lucide-react';

export const PortfolioAnalysisPage: React.FC = () => {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [analysisType, setAnalysisType] = useState<'comprehensive' | 'risk' | 'rebalance'>('comprehensive');
  const [customQuery, setCustomQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | number | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Load portfolio context
  const loadPortfolio = useCallback(async () => {
    if (!portfolioId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [p, h] = await Promise.all([
        portfolioApi.getPortfolio(portfolioId),
        portfolioApi.getHoldings(portfolioId),
      ]);
      setPortfolio(p);
      setHoldings(h);
    } catch (err: any) {
      console.error('Failed to load portfolio:', err);
      setError(err?.message || 'Could not find portfolio.');
    } finally {
      setIsLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const [structuredValuation, setStructuredValuation] = useState<any | null>(null);

  const runAnalysis = async () => {
    if (!portfolio) return;
    setIsGenerating(true);
    setAnalysisError(null);

    let promptFocus = '';
    if (analysisType === 'comprehensive') {
      promptFocus =
        'Perform an institutional-grade comprehensive portfolio diagnostic. Analyze asset quality, diversification across industries, macro sensitivities, earnings exposure, and risk-adjusted growth prospects.';
    } else if (analysisType === 'risk') {
      promptFocus =
        'Perform a quantitative stress test and concentration risk audit. Identify single-stock vulnerabilities, sector overweighting, interest-rate or currency sensitivities, and drawdown risks.';
    } else {
      promptFocus =
        'Provide strategic and tactical rebalancing recommendations. Highlight potential trim/take-profit positions, capital reallocation opportunities, and defensive hedge candidates.';
    }

    if (customQuery.trim()) {
      promptFocus += ` Specific investor query: "${customQuery.trim()}".`;
    }

    try {
      const response = await portfolioApi.analyzePortfolio(portfolio.id, promptFocus);
      const responseText = response.response || 'Analysis generated successfully.';
      setReport(responseText);

      if (response.structured_data?.portfolio) {
        setStructuredValuation(response.structured_data.portfolio);
      }

      if (response.session_id) {
        setSessionId(response.session_id);
      }
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setAnalysisError(err?.response?.data?.error || err?.message || 'Failed to complete AI analysis.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!report) return;
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton height="h-8" width="w-48" />
        <LoadingSkeleton height="h-48" width="w-full" />
      </div>
    );
  }

  if (error || !portfolio) {
    return <ErrorState title="Portfolio Unavailable" message={error || 'Portfolio not found'} onRetry={loadPortfolio} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate(`/app/portfolio/${portfolioId}`)}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-md hover:bg-slate-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to {portfolio.name}</span>
        </button>
      </div>

      <PageHeader
        title={
          <div className="flex items-center gap-2.5">
            <Bot className="w-6 h-6 text-accent-primary" />
            <span>AI Portfolio Audit: {portfolio.name}</span>
          </div>
        }
        subtitle="Multi-agent quantitative risk, sector concentration, and thesis evaluation"
        badge={
          <Badge variant="info" size="sm">
            {holdings.length} {holdings.length === 1 ? 'asset' : 'assets'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            {report && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  leftIcon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                >
                  {copied ? 'Copied' : 'Copy'}
                </Button>
                {sessionId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/app/research/${sessionId}`)}
                    rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
                  >
                    Open in AI Cockpit
                  </Button>
                )}
              </>
            )}
            <Button
              variant="primary"
              size="sm"
              onClick={runAnalysis}
              isLoading={isGenerating}
              leftIcon={<Sparkles className="w-3.5 h-3.5" />}
            >
              {report ? 'Re-Run Audit' : 'Generate AI Audit'}
            </Button>
          </div>
        }
      />

      {/* Configuration Strip */}
      <div className="p-4 bg-surface border border-border-theme rounded-xl space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-text-muted">Analysis Mode:</span>
          <button
            type="button"
            onClick={() => setAnalysisType('comprehensive')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'comprehensive'
                ? 'bg-accent-soft text-accent-primary border-accent-primary/30 font-semibold'
                : 'bg-surface-secondary text-text-muted border-border-subtle hover:text-text-primary'
            }`}
          >
            Comprehensive Audit
          </button>
          <button
            type="button"
            onClick={() => setAnalysisType('risk')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'risk'
                ? 'bg-accent-soft text-accent-primary border-accent-primary/30 font-semibold'
                : 'bg-surface-secondary text-text-muted border-border-subtle hover:text-text-primary'
            }`}
          >
            Stress Test & Concentration
          </button>
          <button
            type="button"
            onClick={() => setAnalysisType('rebalance')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'rebalance'
                ? 'bg-accent-soft text-accent-primary border-accent-primary/30 font-semibold'
                : 'bg-surface-secondary text-text-muted border-border-subtle hover:text-text-primary'
            }`}
          >
            Tactical Rebalancing
          </button>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Specify custom question or focus constraint (e.g. assess earnings beta)..."
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            className="flex-1 bg-surface-secondary text-xs text-text-primary placeholder:text-text-muted border border-border-theme rounded-lg px-3 py-2 focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
          />
        </div>
      </div>

      {analysisError && (
        <div className="p-4 bg-status-danger-soft border border-status-danger/30 text-status-danger text-xs rounded-xl">
          {analysisError}
        </div>
      )}

      {/* Generating State */}
      {isGenerating && (
        <div className="p-12 text-center bg-surface border border-border-theme rounded-xl space-y-4">
          <div className="w-12 h-12 mx-auto rounded-xl bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary">
            <RefreshCw className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-text-primary">
              Synthesizing Portfolio Diagnostic
            </h4>
            <p className="text-xs text-text-muted max-w-md mx-auto mt-1">
              Multi-agent engine is auditing position weights, industry correlations, and valuation multiples...
            </p>
          </div>
        </div>
      )}

      {/* Generated Report */}
      {!isGenerating && report && (
        <div className="space-y-4">
          {structuredValuation && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-surface border border-border-theme rounded-xl">
              <div>
                <span className="text-[10px] font-semibold text-text-muted uppercase">Invested Capital</span>
                <div className="text-sm font-bold font-mono text-text-primary mt-0.5">
                  ₹{Number(structuredValuation.invested_value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-semibold text-text-muted uppercase">Live Market Value</span>
                <div className="text-sm font-bold font-mono text-accent-primary mt-0.5">
                  ₹{Number(structuredValuation.current_value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-semibold text-text-muted uppercase">Live P/L</span>
                <div className={`text-sm font-bold font-mono mt-0.5 ${structuredValuation.profit_loss >= 0 ? 'text-status-success' : 'text-status-danger'}`}>
                  ₹{Number(structuredValuation.profit_loss).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <span className="text-[10px] font-semibold text-text-muted uppercase">Return (%)</span>
                <div className={`text-sm font-bold font-mono mt-0.5 ${structuredValuation.profit_loss >= 0 ? 'text-status-success' : 'text-status-danger'}`}>
                  {structuredValuation.profit_loss_percentage >= 0 ? '+' : ''}
                  {Number(structuredValuation.profit_loss_percentage).toFixed(2)}%
                </div>
              </div>
            </div>
          )}

          <div className="p-6 bg-surface border border-border-theme rounded-xl">
            <MarkdownContent content={report} />
          </div>

          <div className="p-3 bg-surface-secondary border border-border-subtle rounded-lg text-[11px] text-text-muted flex items-center justify-between">
            <span>FinPilot AI quantitative portfolio diagnostic. For informational purposes only.</span>
            <span className="text-text-muted font-mono">Route: portfolio</span>
          </div>
        </div>
      )}

      {/* Uninitiated state */}
      {!isGenerating && !report && !analysisError && (
        <div className="p-12 text-center bg-surface-secondary/40 border border-dashed border-border-theme rounded-xl">
          <Bot className="w-10 h-10 mx-auto text-accent-primary/70 mb-3" />
          <h4 className="text-base font-semibold text-text-primary">
            Audit Ready for {portfolio.name}
          </h4>
          <p className="text-xs text-text-muted max-w-md mx-auto mt-1.5 mb-5 leading-relaxed">
            FinPilot AI will analyze {holdings.length} active positions against real-time fundamental profiles, sector classifications, and market valuation multiples.
          </p>
          <Button
            variant="primary"
            size="md"
            onClick={runAnalysis}
            leftIcon={<Sparkles className="w-4 h-4" />}
          >
            Launch AI Portfolio Audit
          </Button>
        </div>
      )}
    </div>
  );
};
