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
    <div className="bg-surface border border-border-theme rounded-2xl p-5 space-y-4 shadow-card">
      {/* Header with expand/collapse toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent-soft border border-accent-primary/30 text-accent-primary">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-text-primary">
              Quantitative Risk & Optimization Methodology
            </h4>
            <p className="text-xs text-text-muted">
              Authoritative mathematical formulation and conceptual distinctions
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-text-primary transition-colors px-2.5 py-1 rounded-md bg-surface-secondary/60 hover:bg-surface-secondary cursor-pointer border border-border-theme"
        >
          <span>{isOpen ? 'Collapse Details' : 'View Methodology & Disclaimers'}</span>
          {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Core Triad Framework Distinction (Always Visible) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-theme">
          <div className="flex items-center gap-1.5 text-xs font-bold text-text-primary uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-accent-primary" />
            <span>Current Portfolio</span>
          </div>
          <div className="text-xs font-semibold text-accent-primary mb-1">
            "What I currently own."
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">
            The active holdings, share quantities, acquisition cost basis, and current market valuations recorded in your portfolio ledger.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-theme">
          <div className="flex items-center gap-1.5 text-xs font-bold text-text-primary uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-status-warning" />
            <span>Risk Profile</span>
          </div>
          <div className="text-xs font-semibold text-status-warning mb-1">
            "How the current portfolio has behaved historically."
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">
            Statistical observation of historical return variance, downside semi-deviation, peak-to-trough drawdowns, and tail risk (VaR/CVaR).
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-secondary/40 border border-border-theme">
          <div className="flex items-center gap-1.5 text-xs font-bold text-text-primary uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-status-positive" />
            <span>Optimization</span>
          </div>
          <div className="text-xs font-semibold text-status-positive mb-1">
            "What allocation the mathematical optimizer prefers under its assumptions and constraints."
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">
            Theoretical target asset weights derived from Markowitz modern portfolio theory, covariance matrices, and user-specified risk bounds.
          </p>
        </div>
      </div>

      {/* Expanded Methodology & Disclaimers Content */}
      {isOpen && (
        <div className="space-y-4 pt-3 border-t border-border-theme text-xs text-text-secondary leading-relaxed">
          {/* Mathematical Formulations */}
          <div>
            <h5 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
              <Compass className="w-3.5 h-3.5 text-accent-primary" />
              <span>Statistical Formulations (Computed Server-Side)</span>
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-theme space-y-1">
                <span className="font-semibold text-text-primary block">Sharpe Ratio</span>
                <p className="text-text-muted text-[11px]">
                  <code className="text-accent-primary font-mono">(Rp - Rf) / σp</code>: Ratio of excess portfolio return over the risk-free rate to annualized standard deviation. Penalizes both upside and downside volatility equally.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-theme space-y-1">
                <span className="font-semibold text-text-primary block">Sortino Ratio</span>
                <p className="text-text-muted text-[11px]">
                  <code className="text-accent-primary font-mono">(Rp - Rf) / σd</code>: Focuses strictly on harmful downside volatility (semi-deviation of negative returns below benchmark). Does not penalize positive upside shocks.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-theme space-y-1">
                <span className="font-semibold text-text-primary block">Value at Risk (VaR 95%) & CVaR 95%</span>
                <p className="text-text-muted text-[11px]">
                  VaR 95% indicates the maximum expected loss over a specific horizon at a 95% confidence level. CVaR (Conditional VaR / Expected Shortfall) represents the average loss sustained when that 95% threshold is breached.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-theme space-y-1">
                <span className="font-semibold text-text-primary block">Calmar Ratio & Maximum Drawdown</span>
                <p className="text-text-muted text-[11px]">
                  <code className="text-accent-primary font-mono">CAGR / |Max Drawdown|</code>: Measures compound annualized growth rate normalized against the single largest peak-to-trough portfolio equity contraction.
                </p>
              </div>
            </div>
          </div>

          {/* Optimizer Constraints & Assumptions */}
          <div>
            <h5 className="font-semibold text-text-primary mb-2 flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-status-positive" />
              <span>Optimizer Model & Constraints</span>
            </h5>
            <p className="text-text-muted text-[11px] mb-2">
              The mathematical optimizer employs quadratic programming solving for mean-variance efficient portfolios (Markowitz tangency or minimum-variance points). Default assumptions enforce long-only weights (w_i ≥ 0, Σ w_i = 1) with configurable single-asset caps to prevent excessive concentration.
            </p>
          </div>

          {/* Institutional Disclaimers */}
          <div className="p-3.5 rounded-xl bg-status-warning-soft border border-status-warning/20 text-status-warning space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-xs text-status-warning">
              <AlertOctagon className="w-4 h-4 text-status-warning shrink-0" />
              <span>Critical Methodological Disclaimers</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-text-secondary pl-1">
              <li>
                <strong className="text-text-primary">No Guarantee of Future Performance:</strong> Optimized weights represent mathematical optima under historical covariance and return estimates. Historical distributions are non-stationary and do not guarantee future performance or risk mitigation.
              </li>
              <li>
                <strong className="text-text-primary">Frictional Constraints:</strong> Real-world execution involves bid-ask spreads, transaction commissions, market impact, capital gains taxes, and liquidity constraints, which are not modeled in frictionless mean-variance curves.
              </li>
              <li>
                <strong className="text-text-primary">No Automated Trading:</strong> FinPilot AI is an analytical and quantitative decision-support environment. It does not provide trading or trade-execution capabilities.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
