import React from 'react';
import { PortfolioRiskPage } from './PortfolioRiskPage';

/**
 * PortfolioOptimizationPage
 * Dedicated route handler for /app/optimization and /app/portfolio/:portfolioId/optimization
 * Automatically directs the user to the Optimization workspace tab while retaining all quantitative capabilities.
 */
export const PortfolioOptimizationPage: React.FC = () => {
  return <PortfolioRiskPage />;
};
