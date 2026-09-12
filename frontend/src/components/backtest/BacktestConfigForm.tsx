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
  const [inSampleWindow, setInSampleWindow] = useState<number>(252); // ~1 trading year
  const [outOfSampleStep, setOutOfSampleStep] = useState<number>(63); // ~1 trading quarter
  const [transactionCostBps, setTransactionCostBps] = useState<number>(10); // 10 bps = 0.001
  const [riskFreeRatePct, setRiskFreeRatePct] = useState<number>(6.5); // 6.5%
  const [minWeightPct, setMinWeightPct] = useState<number>(0); // 0%
  const [maxWeightPct, setMaxWeightPct] = useState<number>(35); // 35% cap

  // Form error state
  const [validationError, setValidationError] = useState<string | null>(null);

  // Quick preset helper
  const applyPreset = (years: number) => {
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
    setMaxWeightPct(35);
    setValidationError(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={`bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Walk-Forward Backtest Engine Configuration</span>
              <Badge variant="info" size="sm">Authoritative</Badge>
            </h3>
            <p className="text-xs text-slate-400">
              Configure parameters for rolling out-of-sample portfolio re-optimization and benchmark comparison
            </p>
          </div>
        </div>

        {/* Quick Date Presets */}
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <span className="text-[11px] font-mono text-slate-500 px-2">Preset:</span>
          <button
            type="button"
            onClick={() => applyPreset(1)}
            className="px-2 py-1 text-xs rounded hover:bg-slate-800 text-slate-300 transition-colors"
          >
            1Y
          </button>
          <button
            type="button"
            onClick={() => applyPreset(2)}
            className="px-2 py-1 text-xs rounded hover:bg-slate-800 text-slate-300 transition-colors"
          >
            2Y
          </button>
          <button
            type="button"
            onClick={() => applyPreset(3)}
            className="px-2 py-1 text-xs rounded hover:bg-slate-800 text-slate-300 transition-colors"
          >
            3Y
          </button>
          <button
            type="button"
            onClick={() => applyPreset(5)}
            className="px-2 py-1 text-xs rounded hover:bg-slate-800 text-slate-300 transition-colors"
          >
            5Y
          </button>
        </div>
      </div>

      {/* Validation Banner */}
      {validationError && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-400 text-xs">
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
          <label className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
            From Date (Inception)
          </label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => {
              setFromDate(e.target.value);
              setValidationError(null);
            }}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            required
          />
          <span className="text-[10px] text-slate-500 block">Start of historical evaluation</span>
        </div>

        {/* To Date */}
        <div className="space-y-1.5">
          <label className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-cyan-400" />
            To Date (Termination)
          </label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => {
              setToDate(e.target.value);
              setValidationError(null);
            }}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            required
          />
          <span className="text-[10px] text-slate-500 block">End of historical evaluation</span>
        </div>

        {/* Benchmark */}
        <div className="space-y-1.5">
          <label className="font-semibold text-slate-300 block">
            Market Benchmark
          </label>
          <select
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="^NSEI">NIFTY 50 (^NSEI)</option>
            <option value="^BSESN">S&P BSE SENSEX (^BSESN)</option>
            <option value="^NSEBANK">NIFTY Bank (^NSEBANK)</option>
            <option value="SPY">S&P 500 ETF (SPY)</option>
            <option value="QQQ">Invesco QQQ (Nasdaq 100)</option>
          </select>
          <span className="text-[10px] text-slate-500 block">External comparative hurdle</span>
        </div>

        {/* Initial Capital */}
        <div className="space-y-1.5">
          <label className="font-semibold text-slate-300 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            Initial Capital ({portfolioCurrency})
          </label>
          <input
            type="number"
            min="1000"
            step="5000"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            required
          />
          <span className="text-[10px] text-slate-500 block">Starting base equity</span>
        </div>

        {/* Rebalance Frequency */}
        <div className="space-y-1.5">
          <label className="font-semibold text-slate-300 block">
            Rebalance Cadence
          </label>
          <select
            value={rebalanceFrequency}
            onChange={(e) => setRebalanceFrequency(e.target.value as RebalanceFrequency)}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="monthly">Monthly (M)</option>
            <option value="quarterly">Quarterly (Q) — Recommended</option>
            <option value="semi-annually">Semi-Annually (6M)</option>
            <option value="annually">Annually (1Y)</option>
            <option value="weekly">Weekly (W)</option>
          </select>
          <span className="text-[10px] text-slate-500 block">Out-of-sample re-optimization cycle</span>
        </div>

        {/* In-Sample Window */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              In-Sample Window
            </label>
            <span className="font-mono text-cyan-400">{inSampleWindow} days</span>
          </div>
          <input
            type="number"
            min="30"
            max="1260"
            step="21"
            value={inSampleWindow}
            onChange={(e) => setInSampleWindow(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">
            Historical calibration lookback (~{Math.round(inSampleWindow / 21)} months)
          </span>
        </div>

        {/* Out-of-Sample Step */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              Out-of-Sample Step
            </label>
            <span className="font-mono text-emerald-400">{outOfSampleStep} days</span>
          </div>
          <input
            type="number"
            min="5"
            max="252"
            step="5"
            value={outOfSampleStep}
            onChange={(e) => setOutOfSampleStep(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">Forward evaluation window before rebalance</span>
        </div>

        {/* Transaction Cost (bps) */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              Transaction Cost
            </label>
            <span className="font-mono text-amber-400">{transactionCostBps} bps ({(transactionCostBps / 100).toFixed(2)}%)</span>
          </div>
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            value={transactionCostBps}
            onChange={(e) => setTransactionCostBps(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">Brokerage & slippage friction per turnover</span>
        </div>

        {/* Risk-Free Rate */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              Risk-Free Rate ($R_f$)
            </label>
            <span className="font-mono text-slate-300">{riskFreeRatePct}%</span>
          </div>
          <input
            type="number"
            min="0"
            max="20"
            step="0.25"
            value={riskFreeRatePct}
            onChange={(e) => setRiskFreeRatePct(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">Benchmark sovereign yield</span>
        </div>

        {/* Min Weight */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              Min Weight Floor
            </label>
            <span className="font-mono text-slate-300">{minWeightPct}%</span>
          </div>
          <input
            type="number"
            min="0"
            max="50"
            step="1"
            value={minWeightPct}
            onChange={(e) => setMinWeightPct(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">Long-only lower bound</span>
        </div>

        {/* Max Weight */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300 block">
              Max Weight Cap
            </label>
            <span className="font-mono text-slate-300">{maxWeightPct}%</span>
          </div>
          <input
            type="number"
            min="5"
            max="100"
            step="5"
            value={maxWeightPct}
            onChange={(e) => setMaxWeightPct(Number(e.target.value))}
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          />
          <span className="text-[10px] text-slate-500 block">Concentration limit per asset</span>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-4 border-t border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Active Holdings: <strong className="text-white">{portfolioHoldingsCount}</strong></span>
          {portfolioHoldingsCount < 2 && (
            <span className="text-rose-400 text-[11px] font-medium">
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
            className="shadow-lg shadow-cyan-500/20"
          >
            {isLoading ? 'Running Historical Backtest...' : 'Execute Walk-Forward Backtest'}
          </Button>
        </div>
      </div>
    </form>
  );
};
