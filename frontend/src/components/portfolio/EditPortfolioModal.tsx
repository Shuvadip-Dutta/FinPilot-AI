import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Portfolio, UpdatePortfolioPayload, getPortfolioCashBalance } from '../../types/portfolio';

export interface EditPortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: Portfolio | null;
  onSubmit: (data: UpdatePortfolioPayload) => Promise<void>;
  isLoading?: boolean;
}

export const EditPortfolioModal: React.FC<EditPortfolioModalProps> = ({
  isOpen,
  onClose,
  portfolio,
  onSubmit,
  isLoading = false,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [cashBalance, setCashBalance] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (portfolio) {
      setName(portfolio.name || '');
      setDescription(portfolio.description || '');
      setCurrency(portfolio.currency || 'INR');
      const cash = getPortfolioCashBalance(portfolio);
      setCashBalance(cash !== null ? String(cash) : '');
      setError(null);
    }
  }, [portfolio, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Portfolio name is required');
      return;
    }

    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || undefined,
        currency,
        cash_balance: cashBalance ? parseFloat(cashBalance) : undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to update portfolio. Please try again.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Portfolio Details"
      subtitle="Update name, mandate description, and liquidity parameters"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            Save Changes
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
            {error}
          </div>
        )}

        <Input
          label="Portfolio Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <div>
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
            Base Currency
          </label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full bg-slate-900/90 text-slate-100 text-sm rounded-lg border border-slate-700/80 px-3 py-2 focus:outline-none focus:border-cyan-500 transition-colors"
          >
            <option value="INR">INR (₹) — Indian Rupee</option>
            <option value="USD">USD ($) — US Dollar</option>
            <option value="EUR">EUR (€) — Euro</option>
            <option value="GBP">GBP (£) — British Pound</option>
          </select>
        </div>

        <Input
          label="Cash Balance"
          type="number"
          step="any"
          placeholder="0.00"
          value={cashBalance}
          onChange={(e) => setCashBalance(e.target.value)}
          helperText="Total liquid funds available in this portfolio account"
        />

        <div>
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
            Investment Thesis / Description
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-slate-900/90 text-slate-100 placeholder:text-slate-500 text-sm rounded-lg border border-slate-700/80 px-3 py-2 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>
      </form>
    </Modal>
  );
};
