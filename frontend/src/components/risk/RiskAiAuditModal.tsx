import React, { useState } from 'react';
import {
  Portfolio,
  PortfolioRiskResponse,
  PortfolioOptimizationResponse,
  getRiskSharpeRatio,
  getRiskMaxDrawdown,
  getRiskVaR95,
  getRiskCVaR95,
  getRiskVolatility,
  getOptExpectedReturn,
  getOptVolatility,
} from '../../types/portfolio';
import { researchApi } from '../../api/research';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import {
  Sparkles,
  X,
  Send,
  Loader2,
  ShieldAlert,
  Bot,
  AlertTriangle,
  FileText,
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
  optimizationData,
}) => {
  const [analysisText, setAnalysisText] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerateAudit = async () => {
    setIsLoading(true);
    setError(null);

    const sharpe = getRiskSharpeRatio(riskData);
    const maxDd = getRiskMaxDrawdown(riskData);
    const var95 = getRiskVaR95(riskData);
    const cvar95 = getRiskCVaR95(riskData);
    const vol = getRiskVolatility(riskData);
    const optReturn = getOptExpectedReturn(optimizationData);
    const optVol = getOptVolatility(optimizationData);

    const prompt = `You are FinPilot's Senior Portfolio Risk Analyst. Conduct an institutional quantitative risk and allocation audit based strictly on the following authoritative portfolio metrics:

PORTFOLIO: ${portfolio?.name || 'User Portfolio'} (Base Currency: ${portfolio?.currency || 'INR'})
CURRENT QUANTITATIVE RISK PROFILE:
- Sharpe Ratio: ${sharpe !== null ? sharpe.toFixed(2) : 'N/A'}
- Annualized Volatility: ${vol !== null ? `${vol.toFixed(2)}%` : 'N/A'}
- Maximum Drawdown: ${maxDd !== null ? `${maxDd.toFixed(2)}%` : 'N/A'}
- Historical VaR (95% confidence): ${var95 !== null ? `${var95.toFixed(2)}%` : 'N/A'}
- Conditional VaR / Expected Shortfall (95%): ${cvar95 !== null ? `${cvar95.toFixed(2)}%` : 'N/A'}
${
  optimizationData
    ? `MATHEMATICAL OPTIMIZER TARGETS:
- Optimized Expected Return: ${optReturn !== null ? `${optReturn.toFixed(2)}%` : 'N/A'}
- Optimized Volatility: ${optVol !== null ? `${optVol.toFixed(2)}%` : 'N/A'}
- Optimization Objective: ${optimizationData.objective || 'Sharpe Tangency'}`
    : ''
}

Please provide a concise 3-part institutional executive review:
1. Tail Risk & Asymmetric Vulnerability Assessment (evaluate VaR/CVaR vs Drawdown)
2. Risk-Adjusted Efficiency (evaluate Sharpe vs Volatility)
3. Strategic Allocation Commentary & Trade-offs (highlighting that mathematical optimization does not guarantee future results)

Keep the tone analytical, disciplined, and strictly objective without sales language or trading signals.`;

    try {
      const res = await researchApi.chat({
        message: prompt,
      });
      const responseText =
        res.message || res.content || res.response || (res as any).answer || 'Analysis generated successfully.';
      setAnalysisText(typeof responseText === 'string' ? responseText : JSON.stringify(responseText));
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to communicate with the AI audit endpoint. Please check connectivity.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Quantitative Risk & Optimization AI Audit</span>
                <Badge variant="info" size="sm">Institutional AI</Badge>
              </h3>
              <p className="text-xs text-slate-400">
                Qualitative stress commentary powered by backend AI intelligence
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
          {/* Triad Reference */}
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
            <div>
              <span className="text-slate-300 font-semibold">Portfolio:</span> {portfolio?.name || 'Active Ledger'}
            </div>
            <div>
              <span className="text-cyan-300 font-semibold">Authoritative Source:</span> Django Risk Engine
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {analysisText ? (
            <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 text-slate-200 space-y-3 leading-relaxed whitespace-pre-line font-sans">
              {analysisText}
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-3">
              <Bot className="w-8 h-8 text-cyan-500 mx-auto" />
              <div>
                <p className="text-sm font-semibold text-slate-200">
                  Ready to Synthesize Risk Metrics
                </p>
                <p className="text-slate-400 max-w-md mx-auto mt-1">
                  Synthesizes your Sharpe ratio, historical peak-to-trough drawdowns, VaR 95%, and mathematical optimizer weights into an institutional risk commentary.
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={handleGenerateAudit}
                disabled={isLoading}
                leftIcon={isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              >
                {isLoading ? 'Synthesizing Risk Metrics...' : 'Generate Institutional Audit'}
              </Button>
            </div>
          )}

          {/* Institutional Disclaimer */}
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200/90 text-[11px] flex items-start gap-2">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <span>
              AI synthesis provides interpretive analysis of historical metrics and optimizer parameters. It does not provide trading advice, execution commands, or guarantee forward risk resilience.
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
