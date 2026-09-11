import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { MarkdownContent } from '../research/MarkdownContent';
import { Portfolio, Holding, getPortfolioPnL, getPortfolioCurrentValue, getPortfolioInvestedValue } from '../../types/portfolio';
import { researchApi } from '../../api/research';
import { Bot, Sparkles, Copy, Check, ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface PortfolioAiAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: Portfolio | null;
  holdings: Holding[];
}

export const PortfolioAiAnalysisModal: React.FC<PortfolioAiAnalysisModalProps> = ({
  isOpen,
  onClose,
  portfolio,
  holdings,
}) => {
  const navigate = useNavigate();
  const [analysisType, setAnalysisType] = useState<'comprehensive' | 'risk' | 'rebalance'>('comprehensive');
  const [customQuery, setCustomQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Construct prompt from portfolio data
  const handleRunAnalysis = async () => {
    if (!portfolio) return;
    setIsGenerating(true);
    setError(null);

    const holdingsSummary = holdings.map((h, i) => {
      const ticker = h.ticker || h.symbol || 'N/A';
      const qty = h.quantity ?? h.shares ?? 'N/A';
      const buyPrice = h.buy_price ?? h.average_buy_price ?? 'N/A';
      const market = h.market || 'NSE';
      return `${i + 1}. ${ticker} (${market}): ${qty} shares @ avg price ${buyPrice}`;
    }).join('\n');

    const currVal = getPortfolioCurrentValue(portfolio);
    const investedVal = getPortfolioInvestedValue(portfolio);
    const pnl = getPortfolioPnL(portfolio);
    const currency = portfolio.currency || 'INR';

    let promptFocus = '';
    if (analysisType === 'comprehensive') {
      promptFocus = 'Perform an institutional-grade comprehensive portfolio diagnostic. Analyze asset quality, diversification across industries, macro sensitivities, earnings exposure, and risk-adjusted growth prospects.';
    } else if (analysisType === 'risk') {
      promptFocus = 'Perform a quantitative stress test and concentration risk audit. Identify single-stock vulnerabilities, sector overweighting, interest-rate or currency sensitivities, and drawdown risks.';
    } else {
      promptFocus = 'Provide strategic and tactical rebalancing recommendations. Highlight potential trim/take-profit positions, capital reallocation opportunities, and defensive hedge candidates.';
    }

    if (customQuery.trim()) {
      promptFocus += ` Specific investor query: "${customQuery.trim()}".`;
    }

    const fullPrompt = `You are FinPilot AI's Senior Quantitative Portfolio Strategist.
Analyze the following active investor portfolio:
Portfolio Name: ${portfolio.name}
Base Currency: ${currency}
${investedVal !== null ? `Total Cost Basis / Invested: ${currency} ${investedVal}` : ''}
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
      console.error('Failed to run AI portfolio analysis:', err);
      setError(
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
        <div className="flex items-center gap-2 text-cyan-400">
          <Bot className="w-5 h-5 text-cyan-400" />
          <span>FinPilot AI Portfolio Audit</span>
        </div>
      }
      subtitle={`Multi-agent quantitative diagnostic for ${portfolio?.name || 'Portfolio'}`}
      footer={
        <div className="w-full flex items-center justify-between">
          <div className="text-xs text-slate-400">
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
        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">Analysis Focus:</span>
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
              Stress Test & Concentration Risk
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
              Rebalancing & Tactical Alpha
            </button>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Optional: Specify custom question (e.g. How vulnerable are we to rate cuts?)"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              className="flex-1 bg-slate-900 text-xs text-slate-200 placeholder:text-slate-500 border border-slate-700/80 rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
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
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading state */}
        {isGenerating && (
          <div className="p-8 text-center bg-slate-950/40 border border-slate-800 rounded-xl space-y-4">
            <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <RefreshCw className="w-6 h-6 animate-spin" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-200">
                LangGraph Multi-Agent Portfolio Synthesizer Active
              </h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                Evaluating company fundamentals, sector concentrations, valuation multiples, and macro correlations for {portfolio?.name}...
              </p>
            </div>
          </div>
        )}

        {/* Report Content */}
        {!isGenerating && report && (
          <div className="p-5 bg-slate-950/60 border border-slate-800/80 rounded-xl max-h-[55vh] overflow-y-auto">
            <MarkdownContent content={report} />
          </div>
        )}

        {/* Empty placeholder before initial run */}
        {!isGenerating && !report && !error && (
          <div className="p-8 text-center bg-slate-950/20 border border-dashed border-slate-800/80 rounded-xl">
            <Bot className="w-8 h-8 mx-auto text-cyan-400/60 mb-2" />
            <h4 className="text-sm font-semibold text-slate-200">
              Ready to Audit {portfolio?.name}
            </h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
              Select your diagnostic focus and click "Generate AI Audit" to initiate a real-time multi-agent quantitative review of your holdings.
            </p>
          </div>
        )}
      </div>
    </Modal>
  );
};
