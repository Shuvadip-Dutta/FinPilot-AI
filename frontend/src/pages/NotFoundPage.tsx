import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { AlertCircle, ArrowLeft, Sparkles } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-app flex flex-col items-center justify-center p-6 text-center">
      <div className="w-12 h-12 rounded-2xl bg-accent-primary flex items-center justify-center shadow-xs mb-4">
        <Sparkles className="w-6 h-6 text-accent-text stroke-[2.5]" />
      </div>

      <div className="flex items-center gap-2 mb-2 text-status-negative font-mono text-xs font-semibold uppercase tracking-wider">
        <AlertCircle className="w-4 h-4" />
        <span>HTTP 404 — Route Not Found</span>
      </div>

      <h1 className="text-3xl font-extrabold text-text-primary mb-2">Resource Not Found</h1>
      <p className="text-sm text-text-muted max-w-md mb-6 leading-relaxed">
        The terminal route you requested does not exist or has been relocated within the FinPilot AI architecture.
      </p>

      <Link to="/app/dashboard">
        <Button variant="primary" size="md" leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Back to Dashboard
        </Button>
      </Link>
    </div>
  );
};
