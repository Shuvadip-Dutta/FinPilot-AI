import React, { useState } from 'react';
import {
  Portfolio,
  PortfolioRiskResponse,
  PortfolioOptimizationResponse,
  PortfolioStructuredValuation,
  PortfolioRiskMetrics,
  getRiskSharpeRatio,
  getRiskMaxDrawdown,
  getRiskVaR95,
  getRiskCVaR95,
  getRiskVolatility,
  getRiskSortinoRatio,
} from '../../types/portfolio';
import { portfolioApi } from '../../api/portfolio';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { formatCurrency, formatPercent, formatRatio } from '../../utils/formatters';
import {
  Sparkles,
  X,
  Loader2,
  ShieldAlert,
  Bot,
  AlertTriangle,
  Activity,
  TrendingUp,
  Shield,
  Layers,
} from 'lucide-react';

export interface RiskAiAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: Portfolio | null;
  riskData: PortfolioRiskResponse | null;
  optimizationData?: PortfolioOptimizationResponse | null;
}

export const RiskAiAuditModal: React.FC<RiskAiAuditModalProps> = ({
  isOpen,
  onClose,
  portfolio,
  riskData,
}) => {
  const [analysisText, setAnalysisText] = useState<string | null>(null);
  const [valuation, setValuation] = useState<PortfolioStructuredValuation | null>(null);
  const [structuredRisk, setStructuredRisk] = useState<PortfolioRiskMetrics | null>(null);
  const [toolsUsed, setToolsUsed] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerateAudit = async () => {
    if (!portfolio?.id) {
      setError('Portfolio identifier is missing.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await portfolioApi.analyzePortfolio(portfolio.id);
      const responseText = res.response || 'Analysis generated successfully.';
      setAnalysisText(typeof responseText === 'string' ? responseText : JSON.stringify(responseText));

      if (res.structured_data?.portfolio) {
        setValuation(res.structured_data.portfolio);
      }
      if (res.structured_data?.portfolio_risk?.current_risk) {
        setStructuredRisk(res.structured_data.portfolio_risk.current_risk);
      }
      if (res.tools_used && Array.isArray(res.tools_used)) {
        setToolsUsed(res.tools_used);
      }
    } catch (err: any) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to communicate with the AI portfolio audit endpoint. Please check connectivity.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const effectiveRisk: PortfolioRiskResponse | PortfolioRiskMetrics | null =
    structuredRisk || riskData;

  const sharpe = getRiskSharpeRatio(effectiveRisk);
  const sortino = getRiskSortinoRatio(effectiveRisk);
  const vol = getRiskVolatility(effectiveRisk);
  const maxDd = getRiskMaxDrawdown(effectiveRisk);
  const var95 = getRiskVaR95(effectiveRisk);
  const cvar95 = getRiskCVaR95(effectiveRisk);

  const displayCurrency = valuation?.currency || portfolio?.currency || 'INR';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="relative z-10 bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Quantitative Risk & Portfolio AI Audit</span>
                <Badge variant="info" size="sm">Institutional AI</Badge>
              </h3>
              <p className="text-xs text-slate-400">
                Multi-agent qualitative risk synthesis powered by FinPilot Intelligence
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1 text-xs">
          {/* Header Portfolio Reference */}
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
            <div>
              <span className="text-slate-300 font-semibold">Portfolio:</span> {portfolio?.name || 'Active Ledger'}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-cyan-300 font-semibold">Engine:</span>
              <span>Django Risk & AI Agent</span>
            </div>
          </div>

          {/* Structured Portfolio Valuation (if available) */}
          {valuation && (
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  Structured Valuation
                </span>
                <span className="font-mono text-slate-400">
                  {valuation.currency_context || displayCurrency}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono">
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Invested Capital</span>
                  <span className="text-xs font-bold text-slate-200">
                    {formatCurrency(valuation.invested_value, displayCurrency)}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Current Value</span>
                  <span className="text-xs font-bold text-slate-200">
                    {formatCurrency(valuation.current_value, displayCurrency)}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Live P&L</span>
                  <span
                    className={`text-xs font-bold ${
                      valuation.profit_loss >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {formatCurrency(valuation.profit_loss, displayCurrency)}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Total Return</span>
                  <span
                    className={`text-xs font-bold ${
                      valuation.profit_loss_percentage >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {formatPercent(valuation.profit_loss_percentage, true)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Structured Risk Metrics Strip (Authoritative deterministic metrics) */}
          {effectiveRisk && (sharpe !== null || vol !== null || maxDd !== null || var95 !== null) && (
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-cyan-400" />
                  Authoritative Risk Metrics
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  Deterministic Calculation
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 pt-1 font-mono text-center">
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Sharpe</span>
                  <span className="text-xs font-bold text-cyan-300">
                    {sharpe !== null ? formatRatio(sharpe) : '—'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Sortino</span>
                  <span className="text-xs font-bold text-cyan-300">
                    {sortino !== null ? formatRatio(sortino) : '—'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Volatility</span>
                  <span className="text-xs font-bold text-slate-200">
                    {vol !== null ? formatPercent(vol, false) : '—'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Max Drawdown</span>
                  <span className="text-xs font-bold text-rose-400">
                    {maxDd !== null ? formatPercent(maxDd, false) : '—'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">VaR 95%</span>
                  <span className="text-xs font-bold text-amber-400">
                    {var95 !== null ? formatPercent(var95, false) : '—'}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">CVaR 95%</span>
                  <span className="text-xs font-bold text-amber-400">
                    {cvar95 !== null ? formatPercent(cvar95, false) : '—'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tools Used Badge (if available from agent execution) */}
          {toolsUsed.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] text-slate-500 flex items-center gap-1">
                <Layers className="w-3 h-3" /> Agent Tools:
              </span>
              {toolsUsed.map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/40"
                >
                  {tool}
                </span>
              ))}
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* AI Narrative Result or Empty Trigger State */}
          {analysisText ? (
            <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 text-slate-200 space-y-3 leading-relaxed whitespace-pre-line font-sans">
              {analysisText}
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-3">
              <Bot className="w-8 h-8 text-cyan-500 mx-auto" />
              <div>
                <p className="text-sm font-semibold text-slate-200">
                  Ready to Synthesize Portfolio Risk
                </p>
                <p className="text-slate-400 max-w-md mx-auto mt-1">
                  Executes portfolio analysis through the backend AI agent pipeline, synthesizing valuation, historical drawdowns, volatility dispersion, and risk metrics into an institutional review.
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={handleGenerateAudit}
                disabled={isLoading}
                leftIcon={isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              >
                {isLoading ? 'Synthesizing Risk Audit...' : 'Launch Institutional Audit'}
              </Button>
            </div>
          )}

          {/* Institutional Disclaimer */}
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-[11px] flex items-start gap-2">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <span>
              AI synthesis provides qualitative interpretation of authoritative backend metrics. It does not provide trading advice, execution commands, or guarantee forward performance.
            </span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">FinPilot AI Risk Intelligence</span>
          <div className="flex items-center gap-2">
            {analysisText && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleGenerateAudit}
                disabled={isLoading}
              >
                {isLoading ? 'Re-analyzing...' : 'Refresh AI Audit'}
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
