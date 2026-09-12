import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Portfolio, UpdatePortfolioPayload } from '../../types/portfolio';

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (portfolio) {
      setName(portfolio.name || '');
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
      subtitle="Update the portfolio title"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="edit-portfolio-form"
            isLoading={isLoading}
          >
            Save Changes
          </Button>
        </>
      }
    >
      <form id="edit-portfolio-form" onSubmit={handleSubmit} className="space-y-4">
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

        <div className="pt-2 flex justify-end">
          <Button
            variant="primary"
            size="sm"
            type="submit"
            isLoading={isLoading}
          >
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  );
};
