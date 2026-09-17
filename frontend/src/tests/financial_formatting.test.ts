import { formatCurrency, formatRatio, formatPercent, formatFinancialStatementValue } from '../utils/formatters';

function assertEqual(actual: unknown, expected: unknown, message: string): void {
  if (actual !== expected) {
    throw new Error(`${message}: Expected "${expected}", got "${actual}"`);
  }
}

function runFormattingTests(): void {
  console.log('--- RUNNING FINANCIAL NUMBER FORMATTING TESTS ---');

  // 1. Global formatCurrency() Backward-Compatibility Check
  {
    // Global formatCurrency with compact: true only compacts Crores and Lakhs >= 100000
    assertEqual(formatCurrency(54200000, 'INR', { compact: true }), '₹5.42 Cr', 'formatCurrency 5.42 Cr');
    assertEqual(formatCurrency(10000000, 'INR', { compact: true }), '₹1.00 Cr', 'formatCurrency 1.00 Cr');
    assertEqual(formatCurrency(100000, 'INR', { compact: true }), '₹1.00 L', 'formatCurrency 1.00 L');
    // Sub-lakh values must NOT be compacted to Lakhs or Thousands in global formatCurrency
    assertEqual(formatCurrency(95610, 'INR', { compact: true }), '₹95,610.00', 'formatCurrency 95610 remains standard locale currency');
    assertEqual(formatCurrency(94046, 'INR', { compact: true }), '₹94,046.00', 'formatCurrency 94046 remains standard locale currency');
    assertEqual(formatCurrency(8500, 'INR', { compact: true }), '₹8,500.00', 'formatCurrency 8500 remains standard locale currency');
    assertEqual(formatCurrency(500, 'INR'), '₹500.00', 'formatCurrency 500 standard currency');
    assertEqual(formatCurrency(-45000, 'INR', { compact: true }), '-₹45,000.00', 'formatCurrency negative sub-lakh standard currency');
    console.log('PASS: formatCurrency() retains global backward compatibility without new sub-lakh thresholds.');
  }

  // 2. Consistent Compact Financial Statement Formatting inside formatFinancialStatementValue()
  {
    // Values from actual user screenshot:
    // Revenue: 1086181 -> ₹10.86 L
    assertEqual(
      formatFinancialStatementValue('Total Revenue', 'total_revenue', 1086181, 'INR'),
      '₹10.86 L',
      'Screenshot Revenue formatted as ₹10.86 L'
    );
    // Operating Profit: 123162 -> ₹1.23 L
    assertEqual(
      formatFinancialStatementValue('Operating Profit', 'operating_profit', 123162, 'INR'),
      '₹1.23 L',
      'Screenshot Operating Profit formatted as ₹1.23 L'
    );
    // Net Profit: 95610 -> ₹0.96 L (consistent Lakhs display rule)
    assertEqual(
      formatFinancialStatementValue('Net Profit', 'net_profit', 95610, 'INR'),
      '₹0.96 L',
      'Screenshot Net Profit formatted as ₹0.96 L'
    );
    // Depreciation / Tax: 94046 -> ₹0.94 L (consistent Lakhs display rule)
    assertEqual(
      formatFinancialStatementValue('Tax / Depreciation', 'tax_depreciation', 94046, 'INR'),
      '₹0.94 L',
      'Screenshot Tax/Depreciation formatted as ₹0.94 L'
    );

    // Large figures (Crore scale)
    assertEqual(
      formatFinancialStatementValue('Total Assets', 'total_assets', 54200000, 'INR'),
      '₹5.42 Cr',
      'Crore value formatted as ₹5.42 Cr'
    );
    assertEqual(
      formatFinancialStatementValue('Market Cap Base', 'market_cap', 10000000, 'INR'),
      '₹1.00 Cr',
      '1 Cr value formatted as ₹1.00 Cr'
    );

    // Sub-10k thousands scale values
    assertEqual(
      formatFinancialStatementValue('Miscellaneous Expense', 'misc_expense', 8500, 'INR'),
      '₹8.50 K',
      '8.5K value formatted as ₹8.50 K'
    );

    // Base sub-thousand values
    assertEqual(
      formatFinancialStatementValue('Bank Charges', 'bank_charges', 500, 'INR'),
      '₹500.00',
      'Sub-thousand value formatted as standard currency'
    );

    // USD financial statement values formatted as B / M / K
    assertEqual(
      formatFinancialStatementValue('Total Revenue', 'total_revenue', 2500000000, 'USD'),
      '$2.50 B',
      'USD Revenue formatted as $2.50 B'
    );
    assertEqual(
      formatFinancialStatementValue('Net Income', 'net_income', 45000000, 'USD'),
      '$45.00 M',
      'USD Net Income formatted as $45.00 M'
    );
    assertEqual(
      formatFinancialStatementValue('Other Expense', 'other_expense', 8500, 'USD'),
      '$8.50 K',
      'USD Expense formatted as $8.50 K'
    );

    console.log('PASS: formatFinancialStatementValue() produces consistent ₹... L, ₹... Cr, and USD $... B/M/K notation.');
  }

  // 3. Negative Cash Flow and Negative Monetary Statement Values
  {
    assertEqual(
      formatFinancialStatementValue('Operating Cash Flow', 'operating_cash_flow', -45000, 'INR'),
      '-₹0.45 L',
      'Negative sub-lakh formatted with minus prefix'
    );
    assertEqual(
      formatFinancialStatementValue('Investing Cash Flow', 'investing_cash_flow', -1250000, 'INR'),
      '-₹12.50 L',
      'Negative lakh formatted with minus prefix'
    );
    assertEqual(
      formatFinancialStatementValue('Financing Cash Flow', 'financing_cash_flow', -50000000, 'INR'),
      '-₹5.00 Cr',
      'Negative crore formatted with minus prefix'
    );
    assertEqual(
      formatFinancialStatementValue('Other Expense', 'other_expense', -2500, 'INR'),
      '-₹2.50 K',
      'Negative thousands formatted with minus prefix'
    );
    console.log('PASS: Negative statement values remain clearly negative across all scales.');
  }

  // 4. Ratio, Percentage, and Per-Share Fields Contextual Formatting
  {
    // Ratios are NOT treated as currency
    assertEqual(
      formatFinancialStatementValue('Price to Earnings', 'pe_ratio', 24.567, 'INR'),
      '24.57',
      'P/E ratio not formatted as currency'
    );
    assertEqual(
      formatFinancialStatementValue('Price to Book', 'pb_ratio', 3.12, 'INR'),
      '3.12',
      'P/B ratio not formatted as currency'
    );
    assertEqual(
      formatFinancialStatementValue('EV / EBITDA', 'ev_to_ebitda', 14.8, 'INR'),
      '14.80',
      'EV/EBITDA not formatted as currency'
    );
    assertEqual(
      formatFinancialStatementValue('Quick Ratio', 'quick_ratio', 1.25, 'INR'),
      '1.25',
      'Quick Ratio not formatted as currency'
    );
    assertEqual(
      formatFinancialStatementValue('Debt to Equity', 'debt_to_equity', 0.45, 'INR'),
      '0.45',
      'Debt to Equity ratio not formatted as currency'
    );

    // Margins and percentages retain % format
    assertEqual(
      formatFinancialStatementValue('Operating Profit Margin', 'opm_percentage', 18.5, 'INR'),
      '18.50%',
      'Operating margin retains percentage symbol'
    );
    assertEqual(
      formatFinancialStatementValue('Net Profit Margin', 'net_margin', 11.2, 'INR'),
      '11.20%',
      'Net margin retains percentage symbol'
    );
    assertEqual(
      formatFinancialStatementValue('Effective Tax Rate', 'tax_rate', 25.0, 'INR'),
      '25.00%',
      'Tax rate retains percentage symbol'
    );
    assertEqual(
      formatFinancialStatementValue('Return on Equity (ROE)', 'roe', 19.4, 'INR'),
      '19.40%',
      'ROE retains percentage symbol'
    );

    // EPS retains per-share currency format (not compact Lakhs)
    assertEqual(
      formatFinancialStatementValue('Basic EPS', 'eps', 45.2, 'INR'),
      '₹45.20',
      'Basic EPS formatted as standard per-share currency'
    );
    assertEqual(
      formatFinancialStatementValue('Diluted EPS', 'diluted_eps', 44.8, 'INR'),
      '₹44.80',
      'Diluted EPS formatted as standard per-share currency'
    );

    // EPS Growth metrics MUST be formatted as percentages, NOT per-share currency
    assertEqual(
      formatFinancialStatementValue('EPS Growth', 'eps_growth', 15.5, 'INR'),
      '15.50%',
      'EPS Growth classified as percentage, not currency'
    );
    assertEqual(
      formatFinancialStatementValue('Diluted EPS Growth', 'diluted_eps_growth', 12.3, 'INR'),
      '12.30%',
      'Diluted EPS Growth classified as percentage, not currency'
    );
    assertEqual(
      formatFinancialStatementValue('EPS CAGR (3Y)', 'eps_cagr', 18.2, 'INR'),
      '18.20%',
      'EPS CAGR classified as percentage, not currency'
    );

    // Safely handle comma-formatted numeric strings
    assertEqual(
      formatFinancialStatementValue('Net Profit', 'net_profit', '95,610', 'INR'),
      '₹0.96 L',
      'Comma-formatted string 95,610 safely parsed and formatted as ₹0.96 L'
    );
    assertEqual(
      formatFinancialStatementValue('Total Revenue', 'total_revenue', '10,86,181', 'INR'),
      '₹10.86 L',
      'Comma-formatted string 10,86,181 safely parsed and formatted as ₹10.86 L'
    );
    assertEqual(
      formatFinancialStatementValue('Operating Cash Flow', 'operating_cash_flow', '-45,000', 'INR'),
      '-₹0.45 L',
      'Comma-formatted negative string -45,000 safely parsed and formatted as -₹0.45 L'
    );
    assertEqual(
      formatFinancialStatementValue('Operating Expenses', 'operating_expenses', '15,500', 'USD'),
      '$15.50 K',
      'Comma-formatted USD string 15,500 safely parsed and formatted as $15.50 K'
    );

    console.log('PASS: Ratios, percentages, per-share EPS, EPS Growth, and comma-formatted numeric strings correctly classified and formatted.');
  }

  console.log('ALL FINANCIAL NUMBER FORMATTING TESTS PASSED!');
}

runFormattingTests();
