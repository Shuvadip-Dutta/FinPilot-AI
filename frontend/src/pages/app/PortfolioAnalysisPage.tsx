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

  const runAnalysis = async () => {
    if (!portfolio) return;
    setIsGenerating(true);
    setAnalysisError(null);

    const holdingsSummary = holdings
      .map((h, i) => {
        const ticker = h.ticker || h.symbol || 'N/A';
        const qty = h.quantity ?? h.shares ?? 'N/A';
        const buyPrice = h.buy_price ?? h.average_buy_price ?? 'N/A';
        const market = h.market || 'NSE';
        return `${i + 1}. ${ticker} (${market}): ${qty} shares @ avg price ${buyPrice}`;
      })
      .join('\n');

    const currVal = getPortfolioCurrentValue(portfolio);
    const investedVal = getPortfolioInvestedValue(portfolio);
    const pnl = getPortfolioPnL(portfolio);
    const currency = portfolio.currency || 'INR';

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

    const fullPrompt = `You are FinPilot AI's Senior Quantitative Portfolio Strategist.
Analyze the following active investor portfolio:
Portfolio Name: ${portfolio.name}
Base Currency: ${currency}
${investedVal !== null ? `Total Cost Basis: ${currency} ${investedVal}` : ''}
${currVal !== null ? `Current Market Valuation: ${currency} ${currVal}` : ''}
${pnl !== null ? `Total Profit/Loss: ${currency} ${pnl}` : ''}

Current Asset Holdings:
${holdingsSummary || 'No holdings currently registered.'}

Mandate:
${promptFocus}

Please structure your report clearly with:
1. Executive Summary & Quality Score
2. Sector & Thematic Exposure Breakdown
3. Key Concentration & Macro Risks
4. Tactical Recommendations & Rebalancing Ideas`;

    try {
      const primaryMarket = holdings[0]?.market || 'NSE';
      const response = await researchApi.chat({
        message: fullPrompt,
        market: primaryMarket,
        ticker: holdings[0]?.ticker || undefined,
      });

      const responseText = response.message || response.content || response.response || (response as any).answer || 'Analysis generated successfully.';
      setReport(typeof responseText === 'string' ? responseText : JSON.stringify(responseText));
      if (response.session_id) {
        setSessionId(response.session_id);
      }
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setAnalysisError(err?.message || 'Failed to complete AI analysis.');
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
            <Bot className="w-6 h-6 text-cyan-400" />
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
      <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-300">Analysis Mode:</span>
          <button
            type="button"
            onClick={() => setAnalysisType('comprehensive')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'comprehensive'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            Comprehensive Audit
          </button>
          <button
            type="button"
            onClick={() => setAnalysisType('risk')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'risk'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            Stress Test & Concentration
          </button>
          <button
            type="button"
            onClick={() => setAnalysisType('rebalance')}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
              analysisType === 'rebalance'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
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
            className="flex-1 bg-slate-950/80 text-xs text-slate-200 placeholder:text-slate-500 border border-slate-700/80 rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {analysisError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl">
          {analysisError}
        </div>
      )}

      {/* Generating State */}
      {isGenerating && (
        <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-xl space-y-4">
          <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <RefreshCw className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              Synthesizing Portfolio Diagnostic
            </h4>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              Multi-agent engine is auditing position weights, industry correlations, and valuation multiples...
            </p>
          </div>
        </div>
      )}

      {/* Generated Report */}
      {!isGenerating && report && (
        <div className="p-6 bg-slate-900/80 border border-slate-800/90 rounded-xl">
          <MarkdownContent content={report} />
        </div>
      )}

      {/* Uninitiated state */}
      {!isGenerating && !report && !analysisError && (
        <div className="p-12 text-center bg-slate-900/40 border border-dashed border-slate-800 rounded-xl">
          <Bot className="w-10 h-10 mx-auto text-cyan-400/60 mb-3" />
          <h4 className="text-base font-semibold text-slate-200">
            Audit Ready for {portfolio.name}
          </h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1.5 mb-5 leading-relaxed">
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
