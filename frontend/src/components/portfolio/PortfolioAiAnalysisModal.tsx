import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { MarkdownContent } from '../research/MarkdownContent';
import { Portfolio, Holding, getPortfolioPnL, getPortfolioCurrentValue, getPortfolioInvestedValue } from '../../types/portfolio';
import { researchApi } from '../../api/research';
import { portfolioApi } from '../../api/portfolio';
import { formatCurrency, formatPercent } from '../../utils/formatters';
import { Bot, Sparkles, Copy, Check, ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface PortfolioAiAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: Portfolio | null;
  holdings: Holding[];
  onAnalysisSuccess?: (structured: any) => void;
}

export const PortfolioAiAnalysisModal: React.FC<PortfolioAiAnalysisModalProps> = ({
  isOpen,
  onClose,
  portfolio,
  holdings,
  onAnalysisSuccess,
}) => {
  const navigate = useNavigate();
  const [analysisType, setAnalysisType] = useState<'comprehensive' | 'risk' | 'rebalance'>('comprehensive');
  const [customQuery, setCustomQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [structuredValuation, setStructuredValuation] = useState<any | null>(null);
  const [sessionId, setSessionId] = useState<string | number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Run AI portfolio analysis via POST /api/v1/ai/chat/ with portfolio_id
  const handleRunAnalysis = async () => {
    if (!portfolio) return;
    setIsGenerating(true);
    setError(null);

    let promptFocus = '';
    if (analysisType === 'comprehensive') {
      promptFocus = 'Perform an institutional-grade comprehensive portfolio diagnostic. Analyze asset quality, diversification, valuation, and risk-adjusted growth prospects.';
    } else if (analysisType === 'risk') {
      promptFocus = 'Perform a quantitative stress test and concentration risk audit. Identify single-stock vulnerabilities and drawdown risks.';
    } else {
      promptFocus = 'Provide strategic and tactical rebalancing recommendations and capital reallocation opportunities.';
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
        if (onAnalysisSuccess) {
          onAnalysisSuccess(response.structured_data.portfolio);
        }
      }

      if (response.session_id) {
        setSessionId(response.session_id);
      }
    } catch (err: any) {
      console.error('Failed to run AI portfolio analysis:', err);
      setError(
        err?.response?.data?.error ||
        err?.message ||
        'Failed to complete AI portfolio analysis. Please verify your connection to the AI engine.'
      );
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

  const handleOpenInResearch = () => {
    if (sessionId) {
      navigate(`/app/research/${sessionId}`);
    } else {
      navigate('/app/research');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="3xl"
      title={
        <div className="flex items-center gap-2 text-accent-primary">
          <Bot className="w-5 h-5 text-accent-primary" />
          <span>FinPilot AI Portfolio Audit</span>
        </div>
      }
      subtitle={`Multi-agent quantitative diagnostic for ${portfolio?.name || 'Portfolio'}`}
      footer={
        <div className="w-full flex items-center justify-between">
          <div className="text-xs text-text-muted">
            {holdings.length} {holdings.length === 1 ? 'position' : 'positions'} analyzed
          </div>
          <div className="flex items-center gap-2">
            {report && (
              <>
                <Button variant="outline" size="sm" onClick={handleCopy} leftIcon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}>
                  {copied ? 'Copied' : 'Copy Report'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleOpenInResearch}
                  rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
                >
                  Open in AI Cockpit
                </Button>
              </>
            )}
            <Button variant="ghost" size="sm" onClick={onClose} disabled={isGenerating}>
              Close
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Analysis controls header */}
        <div className="p-4 bg-surface-secondary/50 border border-border-theme rounded-xl space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-text-secondary">Analysis Focus:</span>
            <button
              type="button"
              onClick={() => setAnalysisType('comprehensive')}
              className={`px-3 py-1 text-xs rounded-lg border transition-colors cursor-pointer ${
                analysisType === 'comprehensive'
                  ? 'bg-accent-soft text-accent-primary border-accent-primary/40 font-semibold shadow-xs'
                  : 'bg-surface text-text-muted border-border-theme hover:text-text-primary hover:bg-surface-secondary/60'
              }`}
            >
              Comprehensive Audit
            </button>
            <button
              type="button"
              onClick={() => setAnalysisType('risk')}
              className={`px-3 py-1 text-xs rounded-lg border transition-colors cursor-pointer ${
                analysisType === 'risk'
                  ? 'bg-accent-soft text-accent-primary border-accent-primary/40 font-semibold shadow-xs'
                  : 'bg-surface text-text-muted border-border-theme hover:text-text-primary hover:bg-surface-secondary/60'
              }`}
            >
              Stress Test & Concentration Risk
            </button>
            <button
              type="button"
              onClick={() => setAnalysisType('rebalance')}
              className={`px-3 py-1 text-xs rounded-lg border transition-colors cursor-pointer ${
                analysisType === 'rebalance'
                  ? 'bg-accent-soft text-accent-primary border-accent-primary/40 font-semibold shadow-xs'
                  : 'bg-surface text-text-muted border-border-theme hover:text-text-primary hover:bg-surface-secondary/60'
              }`}
            >
              Rebalancing & Tactical Alpha
            </button>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Optional: Specify custom question (e.g. How vulnerable are we to rate cuts?)"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              className="flex-1 bg-surface text-xs text-text-primary placeholder:text-text-muted border border-border-theme rounded-lg px-3 py-2 focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunAnalysis}
              isLoading={isGenerating}
              leftIcon={<Sparkles className="w-3.5 h-3.5" />}
            >
              {report ? 'Re-Run Audit' : 'Generate AI Audit'}
            </Button>
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="p-3 bg-status-negative-soft border border-status-negative/20 text-status-negative text-xs rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading state */}
        {isGenerating && (
          <div className="p-8 text-center bg-surface-secondary/30 border border-border-theme rounded-xl space-y-4">
            <div className="w-12 h-12 mx-auto rounded-xl bg-accent-soft border border-accent-primary/20 flex items-center justify-center text-accent-primary">
              <RefreshCw className="w-6 h-6 animate-spin" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-text-primary">
                LangGraph Multi-Agent Portfolio Synthesizer Active
              </h4>
              <p className="text-xs text-text-muted max-w-md mx-auto mt-1">
                Evaluating company fundamentals, sector concentrations, valuation multiples, and macro correlations for {portfolio?.name}...
              </p>
            </div>
          </div>
        )}

        {/* Report Content */}
        {!isGenerating && report && (
          <div className="space-y-4">
            {structuredValuation && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-surface-secondary/60 border border-border-theme rounded-xl">
                <div>
                  <span className="text-[10px] font-semibold text-text-muted uppercase">Invested Capital</span>
                  <div className="text-sm font-bold font-mono text-text-primary mt-0.5">
                    {formatCurrency(structuredValuation.invested_value, structuredValuation.currency === 'USD' ? 'USD' : 'INR')}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-semibold text-text-muted uppercase">Live Market Value</span>
                  <div className="text-sm font-bold font-mono text-accent-primary mt-0.5">
                    {formatCurrency(structuredValuation.current_value, structuredValuation.currency === 'USD' ? 'USD' : 'INR')}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-semibold text-text-muted uppercase">Live P/L</span>
                  <div className={`text-sm font-bold font-mono mt-0.5 ${structuredValuation.profit_loss >= 0 ? 'text-status-positive' : 'text-status-negative'}`}>
                    {formatCurrency(structuredValuation.profit_loss, structuredValuation.currency === 'USD' ? 'USD' : 'INR')}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-semibold text-text-muted uppercase">Return (%)</span>
                  <div className={`text-sm font-bold font-mono mt-0.5 ${structuredValuation.profit_loss >= 0 ? 'text-status-positive' : 'text-status-negative'}`}>
                    {formatPercent(structuredValuation.profit_loss_percentage, true)}
                  </div>
                </div>
              </div>
            )}

            <div className="p-5 bg-surface-secondary/30 border border-border-theme rounded-xl max-h-[55vh] overflow-y-auto">
              <MarkdownContent content={report} />
            </div>

            <div className="p-3 bg-surface-secondary/50 border border-border-theme rounded-lg text-[11px] text-text-muted flex items-center justify-between">
              <span>FinPilot AI quantitative portfolio diagnostic. For informational purposes only.</span>
              <span className="text-text-muted font-mono">Route: portfolio</span>
            </div>
          </div>
        )}

        {/* Empty placeholder before initial run */}
        {!isGenerating && !report && !error && (
          <div className="p-8 text-center bg-surface-secondary/20 border border-dashed border-border-theme rounded-xl">
            <Bot className="w-8 h-8 mx-auto text-accent-primary mb-2" />
            <h4 className="text-sm font-semibold text-text-primary">
              Ready to Audit {portfolio?.name}
            </h4>
            <p className="text-xs text-text-muted max-w-sm mx-auto mt-1 mb-4">
              Select your diagnostic focus and click "Generate AI Audit" to initiate a real-time multi-agent quantitative review of your holdings.
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunAnalysis}
              isLoading={isGenerating}
              leftIcon={<Sparkles className="w-3.5 h-3.5" />}
            >
              Launch AI Audit
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
};
