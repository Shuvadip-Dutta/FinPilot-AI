import React, { useState } from 'react';
import {
  Calendar,
  Sliders,
  Play,
  RotateCcw,
  DollarSign,
  Layers,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { BacktestPayload, RebalanceFrequency } from '../../types/portfolio';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';

export interface BacktestConfigFormProps {
  portfolioCurrency?: string;
  portfolioHoldingsCount?: number;
  isLoading: boolean;
  onExecute: (config: BacktestPayload) => Promise<void>;
  className?: string;
}

export const BacktestConfigForm: React.FC<BacktestConfigFormProps> = ({
  portfolioCurrency = 'INR',
  portfolioHoldingsCount = 0,
  isLoading,
  onExecute,
  className = '',
}) => {
  // Compute default dates: 2 years back to today
  const getTodayISO = () => new Date().toISOString().split('T')[0];
  const getDateYearsAgo = (years: number) => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - years);
    return d.toISOString().split('T')[0];
  };

  // State
  const [fromDate, setFromDate] = useState<string>(() => getDateYearsAgo(2));
  const [toDate, setToDate] = useState<string>(() => getTodayISO());
  const [benchmark, setBenchmark] = useState<string>('^NSEI');
  const [initialCapital, setInitialCapital] = useState<number>(100000);
  const [rebalanceFrequency, setRebalanceFrequency] = useState<RebalanceFrequency>('quarterly');
  const minAllowedCap = portfolioHoldingsCount > 0 ? Math.ceil(100 / portfolioHoldingsCount) : 50;

  const [inSampleWindow, setInSampleWindow] = useState<number>(252); // ~1 trading year
  const [outOfSampleStep, setOutOfSampleStep] = useState<number>(63); // ~1 trading quarter
  const [transactionCostBps, setTransactionCostBps] = useState<number>(10); // 10 bps = 0.001
  const [riskFreeRatePct, setRiskFreeRatePct] = useState<number>(6.5); // 6.5%
  const [minWeightPct, setMinWeightPct] = useState<number>(0); // 0%
  const [maxWeightPct, setMaxWeightPct] = useState<number>(() =>
    portfolioHoldingsCount > 0 ? Math.max(35, Math.ceil(100 / portfolioHoldingsCount)) : 35
  );

  // Form error state
  const [validationError, setValidationError] = useState<string | null>(null);

  // When portfolioHoldingsCount changes, ensure maxWeightPct is mathematically feasible
  React.useEffect(() => {
    if (portfolioHoldingsCount > 0) {
      const minCap = Math.ceil(100 / portfolioHoldingsCount);
      if (maxWeightPct < minCap) {
        setMaxWeightPct(minCap);
      }
    }
  }, [portfolioHoldingsCount]);

  const [activePreset, setActivePreset] = useState<number | null>(2);

  // Quick preset helper
  const applyPreset = (years: number) => {
    setActivePreset(years);
    setFromDate(getDateYearsAgo(years));
    setToDate(getTodayISO());
    setValidationError(null);
  };

  // Validate inputs strictly before submission
  const validate = (): string | null => {
    if (!fromDate || !toDate) {
      return 'Both Start Date and End Date are required.';
    }
    const start = new Date(fromDate);
    const end = new Date(toDate);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      return 'Please enter valid calendar dates.';
    }
    if (start >= end) {
      return 'Start Date must be strictly prior to End Date.';
    }

    // Minimum range calculation
    const diffDays = Math.round((end.getTime() - start.getTime()) / (1000 * 3600 * 24));
    if (diffDays < 180) {
      return 'Historical backtest requires a minimum span of 180 days for in-sample calibration and out-of-sample evaluation.';
    }

    if (!initialCapital || initialCapital <= 0) {
      return 'Initial capital must be greater than zero.';
    }

    if (inSampleWindow < 30) {
      return 'In-sample calibration window must be at least 30 trading days.';
    }

    if (outOfSampleStep < 5) {
      return 'Out-of-sample evaluation step must be at least 5 trading days.';
    }

    if (minWeightPct < 0 || maxWeightPct > 100) {
      return 'Asset weights must be between 0% and 100%.';
    }

    if (minWeightPct > maxWeightPct) {
      return 'Minimum weight floor cannot exceed maximum weight cap.';
    }

    if (portfolioHoldingsCount > 0 && (maxWeightPct / 100) * portfolioHoldingsCount < 1.0) {
      return `Max Asset Weight Cap (${maxWeightPct}%) is mathematically infeasible for ${portfolioHoldingsCount} holdings. The upper bound must be at least ${minAllowedCap}% so that total weights can sum to 100%.`;
    }

    if (transactionCostBps < 0) {
      return 'Transaction costs cannot be negative.';
    }

    if (portfolioHoldingsCount < 2) {
      return 'Portfolio must contain at least 2 active holdings for multi-asset covariance optimization.';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError(null);

    const payload: BacktestPayload = {
      from_date: fromDate,
      to_date: toDate,
      start_date: fromDate,
      end_date: toDate,
      benchmark_ticker: benchmark,
      benchmark,
      initial_capital: initialCapital,
      rebalance_frequency: rebalanceFrequency,
      in_sample_window_days: inSampleWindow,
      in_sample_window: inSampleWindow,
      out_of_sample_step_days: outOfSampleStep,
      out_of_sample_step: outOfSampleStep,
      transaction_cost_bps: transactionCostBps,
      transaction_cost: transactionCostBps / 10000, // 10 bps -> 0.0010
      risk_free_rate: riskFreeRatePct / 100, // 6.5% -> 0.065
      min_weight: minWeightPct / 100,
      max_weight: maxWeightPct / 100,
    };

    await onExecute(payload);
  };

  const handleReset = () => {
    setActivePreset(2);
    setFromDate(getDateYearsAgo(2));
    setToDate(getTodayISO());
    setBenchmark('^NSEI');
    setInitialCapital(100000);
    setRebalanceFrequency('quarterly');
    setInSampleWindow(252);
    setOutOfSampleStep(63);
    setTransactionCostBps(10);
    setRiskFreeRatePct(6.5);
    setMinWeightPct(0);
    const minCap = portfolioHoldingsCount > 0 ? Math.ceil(100 / portfolioHoldingsCount) : 50;
    setMaxWeightPct(Math.max(35, minCap));
    setValidationError(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`bg-surface border border-border-theme rounded-2xl p-6 shadow-card space-y-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-border-theme">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-accent-soft border border-accent-primary/30 text-accent-primary">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
              <span>Walk-Forward Backtest Engine Configuration</span>
              <Badge variant="info" size="sm">Authoritative</Badge>
            </h3>
            <p className="text-xs text-text-secondary">
              Configure parameters for rolling out-of-sample portfolio re-optimization and benchmark comparison
            </p>
          </div>
        </div>

        {/* Quick Date Presets */}
        <div className="flex items-center gap-1.5 bg-surface-secondary p-1 rounded-lg border border-border-theme">
          <span className="text-[11px] font-mono text-text-muted px-2">Preset:</span>
          {[1, 2, 3, 5].map((yr) => (
            <button
              key={yr}
              type="button"
              onClick={() => applyPreset(yr)}
              className={`px-2.5 py-1 text-xs rounded-md transition-all font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary ${
                activePreset === yr
                  ? 'bg-accent-soft border border-accent-primary text-accent-primary font-semibold shadow-xs'
                  : 'border border-transparent text-text-secondary hover:bg-surface hover:text-text-primary'
              }`}
            >
              {yr}Y
            </button>
          ))}
        </div>
      </div>

      {/* Validation Banner */}
      {validationError && (
        <div className="p-3.5 rounded-xl bg-status-negative-soft border border-status-negative/30 flex items-start gap-3 text-status-negative text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block">Configuration Constraint Violated</span>
            <span>{validationError}</span>
          </div>
        </div>
      )}

      {/* Grid of Configuration Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        {/* From Date */}
        <div className="space-y-1.5">
          <label className="font-semibold text-text-secondary flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-accent-primary" />
            From Date (Inception)
          </label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => {
              setActivePreset(null);
              setFromDate(e.target.value);
              setValidationError(null);
            }}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
            required
          />
          <span className="text-[10px] text-text-muted block">Start of historical evaluation</span>
        </div>

        {/* To Date */}
        <div className="space-y-1.5">
          <label className="font-semibold text-text-secondary flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-accent-primary" />
            To Date (Termination)
          </label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => {
              setActivePreset(null);
              setToDate(e.target.value);
              setValidationError(null);
            }}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
            required
          />
          <span className="text-[10px] text-text-muted block">End of historical evaluation</span>
        </div>

        {/* Benchmark */}
        <div className="space-y-1.5">
          <label className="font-semibold text-text-secondary block">
            Market Benchmark
          </label>
          <select
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 selection:bg-accent-soft selection:text-text-primary"
          >
            <option value="^NSEI">NIFTY 50 (^NSEI)</option>
            <option value="^BSESN">S&P BSE SENSEX (^BSESN)</option>
            <option value="^NSEBANK">NIFTY Bank (^NSEBANK)</option>
            <option value="SPY">S&P 500 ETF (SPY)</option>
            <option value="QQQ">Invesco QQQ (Nasdaq 100)</option>
          </select>
          <span className="text-[10px] text-text-muted block">External comparative hurdle</span>
        </div>

        {/* Initial Capital */}
        <div className="space-y-1.5">
          <label className="font-semibold text-text-secondary flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-status-positive" />
            Initial Capital ({portfolioCurrency})
          </label>
          <input
            type="number"
            min="1000"
            step="5000"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
            required
          />
          <span className="text-[10px] text-text-muted block">Starting base equity</span>
        </div>

        {/* Rebalance Frequency */}
        <div className="space-y-1.5">
          <label className="font-semibold text-text-secondary block">
            Rebalance Cadence
          </label>
          <select
            value={rebalanceFrequency}
            onChange={(e) => setRebalanceFrequency(e.target.value as RebalanceFrequency)}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 selection:bg-accent-soft selection:text-text-primary"
          >
            <option value="monthly">Monthly (M)</option>
            <option value="quarterly">Quarterly (Q) — Recommended</option>
            <option value="semi-annually">Semi-Annually (6M)</option>
            <option value="annually">Annually (1Y)</option>
            <option value="weekly">Weekly (W)</option>
          </select>
          <span className="text-[10px] text-text-muted block">Out-of-sample re-optimization cycle</span>
        </div>

        {/* In-Sample Window */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              In-Sample Window
            </label>
            <span className="font-mono text-accent-primary">{inSampleWindow} days</span>
          </div>
          <input
            type="number"
            min="30"
            max="1260"
            step="21"
            value={inSampleWindow}
            onChange={(e) => setInSampleWindow(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">
            Historical calibration lookback (~{Math.round(inSampleWindow / 21)} months)
          </span>
        </div>

        {/* Out-of-Sample Step */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              Out-of-Sample Step
            </label>
            <span className="font-mono text-status-positive">{outOfSampleStep} days</span>
          </div>
          <input
            type="number"
            min="5"
            max="252"
            step="5"
            value={outOfSampleStep}
            onChange={(e) => setOutOfSampleStep(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">Forward evaluation window before rebalance</span>
        </div>

        {/* Transaction Cost (bps) */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              Transaction Cost
            </label>
            <span className="font-mono text-status-warning">{transactionCostBps} bps ({(transactionCostBps / 100).toFixed(2)}%)</span>
          </div>
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            value={transactionCostBps}
            onChange={(e) => setTransactionCostBps(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">Brokerage & slippage friction per turnover</span>
        </div>

        {/* Risk-Free Rate */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              Risk-Free Rate ($R_f$)
            </label>
            <span className="font-mono text-text-primary">{riskFreeRatePct}%</span>
          </div>
          <input
            type="number"
            min="0"
            max="20"
            step="0.25"
            value={riskFreeRatePct}
            onChange={(e) => setRiskFreeRatePct(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">Benchmark sovereign yield</span>
        </div>

        {/* Min Weight */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              Min Weight Floor
            </label>
            <span className="font-mono text-text-primary">{minWeightPct}%</span>
          </div>
          <input
            type="number"
            min="0"
            max="50"
            step="1"
            value={minWeightPct}
            onChange={(e) => setMinWeightPct(Number(e.target.value))}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">Long-only lower bound</span>
        </div>

        {/* Max Weight */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-text-secondary block">
              Max Weight Cap
            </label>
            <span className="font-mono text-text-primary">{maxWeightPct}%</span>
          </div>
          <input
            type="number"
            min={minAllowedCap}
            max="100"
            step="1"
            value={maxWeightPct}
            onChange={(e) => {
              setMaxWeightPct(Number(e.target.value));
              setValidationError(null);
            }}
            className="w-full bg-surface-secondary border border-border-theme rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30 font-mono selection:bg-accent-soft selection:text-text-primary"
          />
          <span className="text-[10px] text-text-muted block">
            Concentration limit per asset (min {minAllowedCap}% for {portfolioHoldingsCount} holdings)
          </span>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-4 border-t border-border-theme">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <Layers className="w-4 h-4 text-accent-primary" />
          <span>Active Holdings: <strong className="text-text-primary">{portfolioHoldingsCount}</strong></span>
          {portfolioHoldingsCount < 2 && (
            <span className="text-status-negative text-[11px] font-medium">
              (Requires &ge; 2 assets for covariance matrix)
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
            disabled={isLoading}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Reset Defaults
          </Button>

          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            disabled={isLoading || portfolioHoldingsCount < 2}
            leftIcon={<Play className="w-4 h-4 fill-current" />}
            className="shadow-lg shadow-accent-primary/20"
          >
            {isLoading ? 'Running Historical Backtest...' : 'Execute Walk-Forward Backtest'}
          </Button>
        </div>
      </div>
    </form>
  );
};
