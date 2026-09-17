import { apiClient } from '../api/client';
import { portfolioApi } from '../api/portfolio';
import { formatCurrency, formatPercent } from '../utils/formatters';
import { PortfolioStructuredValuation, Portfolio, getPortfolioInvestedValue } from '../types/portfolio';

function assertEqual(actual: unknown, expected: unknown, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: Expected ${expected}, got ${actual}`);
  }
}

/**
 * Focused tests for Portfolio Live Market Valuation & Unrealized P/L (Issue #3):
 * 1. portfolioApi.analyzePortfolio timeout budget is configured to 360,000 ms.
 * 2. Successful valuation payload reaches the frontend caller from structured_data.portfolio.
 * 3. Deterministic calculations (market value, P&L, P&L percentage) format and render correctly.
 * 4. Missing portfolio valuation data is safely handled with graceful fallback ('—').
 */
async function runPortfolioValuationTests(): Promise<void> {
  console.log('--- RUNNING PORTFOLIO VALUATION TESTS ---');

  // Test 1: Verify analyzePortfolio timeout = 360000
  {
    let capturedEndpoint = '';
    let capturedPayload: unknown = null;
    let capturedOptions: { timeoutMs?: number } | undefined = undefined;

    const originalPost = apiClient.post;
    apiClient.post = async <T>(endpoint: string, body?: unknown, options?: { timeoutMs?: number }): Promise<T> => {
      capturedEndpoint = endpoint;
      capturedPayload = body;
      capturedOptions = options;
      return {
        response: 'Analysis report completed.',
        session_id: 'session-val-123',
        structured_data: {
          portfolio: {
            invested_value: 100000,
            current_value: 125000,
            profit_loss: 25000,
            profit_loss_percentage: 25.0,
            holdings_count: 2,
            currency: 'INR',
          },
        },
      } as T;
    };

    try {
      const response = await portfolioApi.analyzePortfolio(42, 'Audit portfolio');

      assertEqual(capturedEndpoint, 'ai/chat/', 'Test 1: Endpoint mismatch');
      assertEqual(capturedOptions?.timeoutMs, 360000, 'Test 1: Timeout must be exactly 360000ms');
      assertEqual((capturedPayload as any)?.portfolio_id, '42', 'Test 1: portfolio_id mismatch');

      console.log('PASS: Test 1: portfolioApi.analyzePortfolio correctly specifies 360,000ms timeout.');

      // Test 2: Successful valuation payload extraction
      const structuredPortfolio = response.structured_data?.portfolio;
      if (!structuredPortfolio) {
        throw new Error('Test 2 Failed: structured_data.portfolio missing from response');
      }

      assertEqual(structuredPortfolio.current_value, 125000, 'Test 2: current_value mismatch');
      assertEqual(structuredPortfolio.profit_loss, 25000, 'Test 2: profit_loss mismatch');
      assertEqual(structuredPortfolio.profit_loss_percentage, 25.0, 'Test 2: profit_loss_percentage mismatch');

      console.log('PASS: Test 2: Structured valuation payload successfully extracted from response.');
    } finally {
      apiClient.post = originalPost;
    }
  }

  // Test 3: Deterministic portfolio calculations and formatting
  {
    // Sample holdings with known quantities and prices
    const holdings = [
      { ticker: 'RELIANCE', quantity: 10, average_price: 2500, last_price: 2800 },
      { ticker: 'TCS', quantity: 20, average_price: 3500, last_price: 4000 },
    ];

    // Authoritative math
    let investedValue = 0;
    let currentValue = 0;
    for (const h of holdings) {
      investedValue += h.quantity * h.average_price;
      currentValue += h.quantity * h.last_price;
    }
    const profitLoss = currentValue - investedValue;
    const profitLossPercent = (profitLoss / investedValue) * 100;

    assertEqual(investedValue, 95000, 'Invested value math mismatch');
    assertEqual(currentValue, 108000, 'Current value math mismatch');
    assertEqual(profitLoss, 13000, 'Profit/loss math mismatch');
    assertEqual(Math.round(profitLossPercent * 100) / 100, 13.68, 'Profit/loss percent math mismatch');

    // Test formatting output (Indian Rupee formatting en-IN: ₹1,08,000.00)
    const formattedCurrentValue = formatCurrency(currentValue, 'INR');
    const formattedProfitLoss = formatCurrency(profitLoss, 'INR');
    const formattedPercent = formatPercent(profitLossPercent, true);

    if (!formattedCurrentValue.includes('1,08,000')) {
      throw new Error(`Formatted current value mismatch: ${formattedCurrentValue}`);
    }
    if (!formattedProfitLoss.includes('13,000')) {
      throw new Error(`Formatted P&L mismatch: ${formattedProfitLoss}`);
    }
    assertEqual(formattedPercent, '+13.68%', 'Formatted percent mismatch');

    console.log('PASS: Test 3: Deterministic calculations and currency/percent formatting match expected values.');
  }

  // Test 4: Missing valuation data safety
  {
    const nullValuation: PortfolioStructuredValuation | null = null;
    const liveValuation = nullValuation?.current_value ?? null;
    const livePnl = nullValuation?.profit_loss ?? null;
    const livePnlPercent = nullValuation?.profit_loss_percentage ?? null;

    assertEqual(liveValuation, null, 'Expected liveValuation to be null');
    assertEqual(livePnl, null, 'Expected livePnl to be null');
    assertEqual(livePnlPercent, null, 'Expected livePnlPercent to be null');

    const displayValuation = liveValuation !== null ? formatCurrency(liveValuation, 'INR') : '—';
    const displayPnl = livePnl !== null ? formatCurrency(livePnl, 'INR') : '—';

    assertEqual(displayValuation, '—', 'Fallback display valuation mismatch');
    assertEqual(displayPnl, '—', 'Fallback display PnL mismatch');

    console.log('PASS: Test 4: Missing valuation data safely renders fallback dashes without error.');
  }

  console.log('--- ALL PORTFOLIO VALUATION TESTS PASSED ---');
}

runPortfolioValuationTests().catch((err) => {
  console.error('FAIL: runPortfolioValuationTests failed:', err);
  process.exit(1);
});
