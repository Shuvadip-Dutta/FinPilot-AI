import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  BookOpen,
  ArrowDown,
  Layers,
  ShieldAlert,
  GitBranch,
  Repeat,
  DollarSign,
  Award,
} from 'lucide-react';
import { Badge } from '../common/Badge';

export interface BacktestMethodologyPanelProps {
  className?: string;
  defaultExpanded?: boolean;
}

export const BacktestMethodologyPanel: React.FC<BacktestMethodologyPanelProps> = ({
  className = '',
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`bg-surface border border-border-theme rounded-2xl overflow-hidden shadow-card ${className}`}>
      {/* Header Button */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left p-5 flex items-center justify-between gap-4 hover:bg-surface-secondary/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-accent-soft border border-accent-primary/30 text-accent-primary">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-text-primary flex items-center gap-2">
              <span>How the Walk-Forward Backtest Works</span>
              <Badge variant="info" size="sm">Methodology & Limits</Badge>
            </h4>
            <p className="text-xs text-text-secondary">
              Understanding rolling out-of-sample evaluation, transaction friction, and baseline benchmarks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-accent-primary">
          <span>{isExpanded ? 'Collapse' : 'Expand Explanation'}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expandable Body */}
      {isExpanded && (
        <div className="p-6 border-t border-border-theme bg-surface-secondary/40 space-y-6 text-xs text-text-secondary leading-relaxed">
          {/* 1. Walk-Forward Cycle Flow */}
          <div className="space-y-3">
            <h5 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Repeat className="w-4 h-4 text-accent-primary" />
              <span>Walk-Forward Pipeline Flowchart</span>
            </h5>
            <div className="p-4 rounded-xl bg-surface border border-border-theme flex flex-col md:flex-row items-center justify-between gap-2 text-center text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-theme w-full md:w-auto">
                <span className="text-text-muted text-[10px] block">Step 1</span>
                <strong className="text-text-primary">Historical Data</strong>
              </div>
              <ArrowDown className="w-4 h-4 text-text-muted rotate-0 md:-rotate-90 shrink-0" />

              <div className="p-2.5 rounded-lg bg-accent-soft border border-accent-primary/30 w-full md:w-auto">
                <span className="text-accent-primary text-[10px] block">Step 2</span>
                <strong className="text-accent-primary">In-Sample Calibration</strong>
              </div>
              <ArrowDown className="w-4 h-4 text-text-muted rotate-0 md:-rotate-90 shrink-0" />

              <div className="p-2.5 rounded-lg bg-surface-secondary border border-border-theme w-full md:w-auto">
                <span className="text-text-muted text-[10px] block">Step 3</span>
                <strong className="text-text-primary">Solve Target Weights</strong>
              </div>
              <ArrowDown className="w-4 h-4 text-text-muted rotate-0 md:-rotate-90 shrink-0" />

              <div className="p-2.5 rounded-lg bg-status-positive-soft border border-status-positive/30 w-full md:w-auto">
                <span className="text-status-positive text-[10px] block">Step 4</span>
                <strong className="text-status-positive">Out-of-Sample Evaluation</strong>
              </div>
              <ArrowDown className="w-4 h-4 text-text-muted rotate-0 md:-rotate-90 shrink-0" />

              <div className="p-2.5 rounded-lg bg-status-warning-soft border border-status-warning/30 w-full md:w-auto">
                <span className="text-status-warning text-[10px] block">Step 5</span>
                <strong className="text-status-warning">Transaction Friction</strong>
              </div>
              <ArrowDown className="w-4 h-4 text-text-muted rotate-0 md:-rotate-90 shrink-0" />

              <div className="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/30 w-full md:w-auto">
                <span className="text-purple-400 text-[10px] block">Step 6</span>
                <strong className="text-purple-300">Rebalance & Roll</strong>
              </div>
            </div>
          </div>

          {/* 2. Core Archetypes Definition */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-surface border border-accent-primary/30 space-y-1.5">
              <div className="flex items-center gap-2 text-accent-primary font-bold">
                <GitBranch className="w-4 h-4" />
                <span>Strategy (Rolling WF)</span>
              </div>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                The actively evaluated systematic portfolio. At each rebalance boundary, the mathematical optimizer calibrates on the preceding in-sample lookback window, solves for optimal risk-adjusted weights, and holds them forward into the unseen out-of-sample period.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-surface border border-status-warning/30 space-y-1.5">
              <div className="flex items-center gap-2 text-status-warning font-bold">
                <Layers className="w-4 h-4" />
                <span>Buy & Hold Baseline</span>
              </div>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                The static benchmark reflecting your original portfolio allocation deployed on day one and left unadjusted without periodic rebalancing. Useful for evaluating whether dynamic rebalancing adds genuine alpha after accounting for turnover friction.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-surface border border-purple-500/30 space-y-1.5">
              <div className="flex items-center gap-2 text-purple-400 font-bold">
                <Award className="w-4 h-4" />
                <span>External Benchmark</span>
              </div>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                A broad market index (e.g., NIFTY 50, S&P 500) representing the passive opportunity cost. Relative metrics like Tracking Error and Information Ratio measure how closely and efficiently the strategy generates excess returns against this index.
              </p>
            </div>
          </div>

          {/* 3. In-Sample vs Out-of-Sample Discipline */}
          <div className="space-y-2">
            <h5 className="text-xs font-bold uppercase tracking-wider text-text-primary">
              In-Sample Calibration vs Out-of-Sample Evaluation
            </h5>
            <p className="text-text-secondary">
              A standard backtest that uses the full historical dataset to find one static set of optimal weights commits <strong className="text-text-primary">lookahead bias</strong> (evaluating decisions using future data that was unavailable at the time).
            </p>
            <ul className="list-disc pl-5 space-y-1 text-text-secondary text-[11px]">
              <li>
                <strong className="text-text-primary">In-Sample Data:</strong> Serves exclusively as calibration inputs to estimate covariance matrices and expected return vectors.
              </li>
              <li>
                <strong className="text-text-primary">Out-of-Sample Data:</strong> Completely withheld from the optimizer during calibration. Realized portfolio returns are evaluated strictly across this forward interval to replicate real-world forward execution.
              </li>
              <li>
                <strong className="text-text-primary">Transaction Costs:</strong> Deducted from capital whenever weights are adjusted, penalizing excessive turnover and short-term churn.
              </li>
            </ul>
          </div>

          {/* 4. Regulatory & Model Limits Disclaimer */}
          <div className="p-4 rounded-xl bg-status-warning-soft border border-status-warning/30 flex items-start gap-3 text-status-warning text-xs">
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold block">Important Quantitative Evaluation Disclaimers</span>
              <p className="text-text-secondary text-[11px] leading-relaxed">
                Historical backtesting is an analytical evaluation of mathematical models over historical data regimes. Realized past performance does not guarantee future results. Covariance structures and correlation regimes are non-stationary and may break down during market dislocations. This engine does not execute live orders or provide investment advice.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
