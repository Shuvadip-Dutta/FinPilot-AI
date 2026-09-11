import React, { useState } from 'react';
import {
  HelpCircle,
  Shield,
  Sliders,
  AlertOctagon,
  ChevronDown,
  ChevronUp,
  Scale,
  Compass,
} from 'lucide-react';

export const MethodologyPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-4">
      {/* Header with expand/collapse toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              Quantitative Risk & Optimization Methodology
            </h4>
            <p className="text-xs text-slate-400">
              Authoritative mathematical formulation and conceptual distinctions
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors px-2.5 py-1 rounded-md bg-slate-800/50 hover:bg-slate-800"
        >
          <span>{isOpen ? 'Collapse Details' : 'View Methodology & Disclaimers'}</span>
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Core Triad Framework Distinction (Always Visible) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>Current Portfolio</span>
          </div>
          <div className="text-xs font-semibold text-cyan-300 mb-1">
            "What I currently own."
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            The active holdings, share quantities, acquisition cost basis, and current market valuations recorded in your portfolio ledger.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>Risk Profile</span>
          </div>
          <div className="text-xs font-semibold text-amber-300 mb-1">
            "How the current portfolio has behaved historically."
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Statistical observation of historical return variance, downside semi-deviation, peak-to-trough drawdowns, and tail risk (VaR/CVaR).
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Optimization</span>
          </div>
          <div className="text-xs font-semibold text-emerald-300 mb-1">
            "What allocation the mathematical optimizer prefers under its assumptions and constraints."
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Theoretical target asset weights derived from Markowitz modern portfolio theory, covariance matrices, and user-specified risk bounds.
          </p>
        </div>
      </div>

      {/* Expanded Methodology & Disclaimers Content */}
      {isOpen && (
        <div className="space-y-4 pt-3 border-t border-slate-800/80 text-xs text-slate-300 leading-relaxed">
          {/* Mathematical Formulations */}
          <div>
            <h5 className="font-semibold text-slate-200 mb-2 flex items-center gap-2">
              <Compass className="w-3.5 h-3.5 text-cyan-400" />
              <span>Statistical Formulations (Computed Server-Side)</span>
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60 space-y-1">
                <span className="font-semibold text-slate-200 block">Sharpe Ratio</span>
                <p className="text-slate-400 text-[11px]">
                  <code className="text-cyan-300 font-mono">(Rp - Rf) / σp</code>: Ratio of excess portfolio return over the risk-free rate to annualized standard deviation. Penalizes both upside and downside volatility equally.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60 space-y-1">
                <span className="font-semibold text-slate-200 block">Sortino Ratio</span>
                <p className="text-slate-400 text-[11px]">
                  <code className="text-cyan-300 font-mono">(Rp - Rf) / σd</code>: Focuses strictly on harmful downside volatility (semi-deviation of negative returns below benchmark). Does not penalize positive upside shocks.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60 space-y-1">
                <span className="font-semibold text-slate-200 block">Value at Risk (VaR 95%) & CVaR 95%</span>
                <p className="text-slate-400 text-[11px]">
                  VaR 95% indicates the maximum expected loss over a specific horizon at a 95% confidence level. CVaR (Conditional VaR / Expected Shortfall) represents the average loss sustained when that 95% threshold is breached.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/60 space-y-1">
                <span className="font-semibold text-slate-200 block">Calmar Ratio & Maximum Drawdown</span>
                <p className="text-slate-400 text-[11px]">
                  <code className="text-cyan-300 font-mono">CAGR / |Max Drawdown|</code>: Measures compound annualized growth rate normalized against the single largest peak-to-trough portfolio equity contraction.
                </p>
              </div>
            </div>
          </div>

          {/* Optimizer Constraints & Assumptions */}
          <div>
            <h5 className="font-semibold text-slate-200 mb-2 flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-emerald-400" />
              <span>Optimizer Model & Constraints</span>
            </h5>
            <p className="text-slate-400 text-[11px] mb-2">
              The mathematical optimizer employs quadratic programming solving for mean-variance efficient portfolios (Markowitz tangency or minimum-variance points). Default assumptions enforce long-only weights (w_i ≥ 0, Σ w_i = 1) with configurable single-asset caps to prevent excessive concentration.
            </p>
          </div>

          {/* Institutional Disclaimers */}
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-xs text-amber-300">
              <AlertOctagon className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Critical Methodological Disclaimers</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-200/90 pl-1">
              <li>
                <strong>No Guarantee of Future Performance:</strong> Optimized weights represent mathematical optima under historical covariance and return estimates. Historical distributions are non-stationary and do not guarantee future performance or risk mitigation.
              </li>
              <li>
                <strong>Frictional Constraints:</strong> Real-world execution involves bid-ask spreads, transaction commissions, market impact, capital gains taxes, and liquidity constraints, which are not modeled in frictionless mean-variance curves.
              </li>
              <li>
                <strong>No Automated Trading:</strong> FinPilot AI is an analytical and quantitative decision-support environment. It does not provide trading or trade-execution capabilities.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
