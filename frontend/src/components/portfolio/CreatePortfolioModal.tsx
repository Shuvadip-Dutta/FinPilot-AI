import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { CreatePortfolioPayload } from '../../types/portfolio';

export interface CreatePortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreatePortfolioPayload) => Promise<void>;
  isLoading?: boolean;
}

export const CreatePortfolioModal: React.FC<CreatePortfolioModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

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
      setName('');
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to create portfolio. Please try again.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Portfolio"
      subtitle="Establish a new asset ledger and tracking book"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="create-portfolio-form"
            isLoading={isLoading}
          >
            Create Portfolio
          </Button>
        </>
      }
    >
      <form id="create-portfolio-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
            {error}
          </div>
        )}

        <Input
          label="Portfolio Name"
          placeholder="e.g. Core India Growth, Tech Alpha, Momentum 50"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          autoFocus
        />

        <div className="pt-2 flex justify-end">
          <Button
            variant="primary"
            size="sm"
            type="submit"
            isLoading={isLoading}
          >
            Create Portfolio
          </Button>
        </div>
      </form>
    </Modal>
  );
};
