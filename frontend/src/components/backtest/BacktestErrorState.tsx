import React from 'react';
import { AlertTriangle, RefreshCw, Briefcase, Calendar, ShieldAlert } from 'lucide-react';
import { Button } from '../common/Button';

export interface BacktestErrorStateProps {
  error: string | null;
  status?: number;
  onRetry?: () => void;
  onResetConfig?: () => void;
  onCreatePortfolio?: () => void;
}

export const BacktestErrorState: React.FC<BacktestErrorStateProps> = ({
  error,
  status,
  onRetry,
  onResetConfig,
  onCreatePortfolio,
}) => {
  // Determine user-friendly category and message
  const isAuthError = status === 401 || (error && /unauthorized|token|authentication/i.test(error));
  const isForbidden = status === 403 || (error && /forbidden|permission/i.test(error));
  const isNotFound = status === 404 || (error && /not found/i.test(error));
  const isRateLimit = status === 429 || (error && /rate limit|too many requests/i.test(error));
  const isTimeout = status === 408 || status === 504 || (error && /timeout|network|took longer/i.test(error));
  const isInsufficientData = error && /insufficient|not enough|history|price data|lookback/i.test(error);
  const isNoPortfolio = error && /create a portfolio|no portfolio/i.test(error);

  let title = 'Historical Evaluation Could Not Be Completed';
  let description =
    error || 'An unexpected error occurred while executing the walk-forward backtest on the backend.';

  if (isNoPortfolio) {
    title = 'Portfolio Required';
    description = 'Create or register a portfolio with active stock holdings before running a walk-forward backtest.';
  } else if (isInsufficientData) {
    title = 'Insufficient Historical Data';
    description =
      'Not enough historical price series are available for the selected in-sample lookback window and asset holdings. Try shortening the in-sample window or adjusting the start date.';
  } else if (isRateLimit) {
    title = 'Evaluation Rate Limit Exceeded';
    description = 'Multiple intensive mathematical optimizations were dispatched. Please wait a moment before re-submitting.';
  } else if (isAuthError) {
    title = 'Authentication Session Expired';
    description = 'Your session token has expired or is invalid. Please refresh or re-authenticate to continue.';
  } else if (isForbidden) {
    title = 'Access Restricted';
    description = 'You do not have permission to execute quantitative backtesting on this portfolio.';
  } else if (isNotFound) {
    title = 'Portfolio or Endpoint Not Found';
    description = 'The target portfolio or backtesting engine endpoint could not be resolved on the backend.';
  } else if (isTimeout) {
    title = 'Evaluation Timed Out';
    description =
      'The walk-forward evaluation took longer than the server timeout limit. Consider selecting a shorter date range or quarterly rebalancing.';
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center max-w-xl mx-auto shadow-xl">
      <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto mb-4 text-rose-400">
        {isInsufficientData ? (
          <Calendar className="w-6 h-6" />
        ) : isNoPortfolio ? (
          <Briefcase className="w-6 h-6" />
        ) : isRateLimit || isForbidden ? (
          <ShieldAlert className="w-6 h-6" />
        ) : (
          <AlertTriangle className="w-6 h-6" />
        )}
      </div>

      <h3 className="text-base font-bold text-white mb-2">{title}</h3>
      <p className="text-xs text-slate-400 max-w-md mx-auto mb-6 leading-relaxed">
        {description}
      </p>

      <div className="flex items-center justify-center gap-3 flex-wrap">
        {isNoPortfolio && onCreatePortfolio && (
          <Button
            variant="primary"
            size="sm"
            onClick={onCreatePortfolio}
            leftIcon={<Briefcase className="w-4 h-4" />}
          >
            Create Portfolio
          </Button>
        )}

        {onRetry && !isNoPortfolio && (
          <Button
            variant="primary"
            size="sm"
            onClick={onRetry}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Retry Evaluation
          </Button>
        )}

        {onResetConfig && (
          <Button
            variant="outline"
            size="sm"
            onClick={onResetConfig}
          >
            Adjust Configuration
          </Button>
        )}
      </div>
    </div>
  );
};
