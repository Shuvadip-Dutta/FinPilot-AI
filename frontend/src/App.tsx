import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { PublicRoute } from './routes/PublicRoute';
import { AppShell } from './components/layout/AppShell';

// Auth Pages
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';

// App Pages
import { DashboardPage } from './pages/app/DashboardPage';
import { ResearchPage } from './pages/app/ResearchPage';
import { ResearchHistoryPage } from './pages/app/ResearchHistoryPage';
import { ResearchSessionDetailPage } from './pages/app/ResearchSessionDetailPage';
import { MarketsPage } from './pages/app/MarketsPage';
import { PortfoliosListPage } from './pages/app/PortfoliosListPage';
import { PortfolioDetailPage } from './pages/app/PortfolioDetailPage';
import { PortfolioAnalysisPage } from './pages/app/PortfolioAnalysisPage';
import { PortfolioRiskPage } from './pages/app/PortfolioRiskPage';
import { PortfolioOptimizationPage } from './pages/app/PortfolioOptimizationPage';
import { BacktestPage } from './pages/app/BacktestPage';
import { PortfolioAlertsPage } from './pages/app/PortfolioAlertsPage';
import { DocumentsPage } from './pages/app/DocumentsPage';
import { PlaceholderPage } from './pages/app/PlaceholderPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ThemeProvider } from './context/ThemeContext';

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/app/dashboard" replace />} />

          {/* Public Authentication Routes */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            }
          />

          {/* Protected Application Terminal Shell */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />

            {/* AI Research Routes (Phase B) */}
            <Route path="research" element={<ResearchPage />} />
            <Route path="research/history" element={<ResearchHistoryPage />} />
            <Route path="research/:sessionId" element={<ResearchSessionDetailPage />} />
            <Route path="documents" element={<DocumentsPage />} />

            {/* Markets & News Routes (Phase B) */}
            <Route path="markets" element={<MarketsPage />} />

            {/* Portfolio Routes (Phase C) */}
            <Route path="portfolio" element={<PortfoliosListPage />} />
            <Route path="portfolio/:portfolioId" element={<PortfolioDetailPage />} />
            <Route path="portfolio/:portfolioId/analysis" element={<PortfolioAnalysisPage />} />
            <Route path="portfolio/:portfolioId/risk" element={<PortfolioRiskPage />} />
            <Route path="portfolio/:portfolioId/optimization" element={<PortfolioOptimizationPage />} />
            <Route path="portfolio/:portfolioId/backtest" element={<BacktestPage />} />
            <Route path="portfolio/:portfolioId/alerts" element={<PortfolioAlertsPage />} />

            {/* Quantitative Risk & Optimization Routes (Phase D) */}
            <Route path="risk" element={<PortfolioRiskPage />} />
            <Route path="risk/:portfolioId" element={<PortfolioRiskPage />} />
            <Route path="optimization" element={<PortfolioOptimizationPage />} />
            <Route path="optimization/:portfolioId" element={<PortfolioOptimizationPage />} />

            {/* Portfolio Alert Center (Module 15) */}
            <Route path="alerts" element={<PortfolioAlertsPage />} />
            <Route path="alerts/:portfolioId" element={<PortfolioAlertsPage />} />

            {/* Backtest Workspace (Phase E) */}
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="backtest/:portfolioId" element={<BacktestPage />} />

            {/* User Profile & System Settings */}
            <Route path="profile" element={<PlaceholderPage />} />
            <Route path="settings" element={<PlaceholderPage />} />
          </Route>

          {/* 404 Catch-All */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
    </ThemeProvider>
  );
}
