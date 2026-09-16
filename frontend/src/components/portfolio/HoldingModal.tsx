import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import { Holding, CreateHoldingPayload } from '../../types/portfolio';

export interface HoldingModalProps {
  isOpen: boolean;
  onClose: () => void;
  holding?: Holding | null; // null for add mode, holding for edit mode
  currency?: string;
  onSubmit: (data: CreateHoldingPayload) => Promise<void>;
  isLoading?: boolean;
}

export const HoldingModal: React.FC<HoldingModalProps> = ({
  isOpen,
  onClose,
  holding,
  currency = 'INR',
  onSubmit,
  isLoading = false,
}) => {
  const isEdit = Boolean(holding);

  const [ticker, setTicker] = useState('');
  const [market, setMarket] = useState<'IN' | 'US'>('IN');
  const [quantity, setQuantity] = useState('');
  const [averagePrice, setAveragePrice] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (holding) {
      setTicker(holding.ticker || '');
      setMarket((holding.market as 'IN' | 'US') || 'IN');
      const qty = holding.quantity ?? '';
      setQuantity(String(qty));
      const price = holding.average_price ?? '';
      setAveragePrice(String(price));
      setError(null);
    } else {
      setTicker('');
      setMarket('IN');
      setQuantity('');
      setAveragePrice('');
      setError(null);
    }
  }, [holding, isOpen, currency]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!ticker.trim()) {
      setError('Ticker symbol is required');
      return;
    }

    const parsedQty = parseFloat(quantity);
    if (isNaN(parsedQty) || parsedQty <= 0) {
      setError('Please enter a valid quantity greater than 0');
      return;
    }

    const parsedPrice = parseFloat(averagePrice);
    if (isNaN(parsedPrice) || parsedPrice <= 0) {
      setError('Please enter a valid average buy price greater than 0');
      return;
    }

    setError(null);
    try {
      await onSubmit({
        ticker: ticker.trim().toUpperCase(),
        market,
        quantity: parsedQty,
        average_price: parsedPrice,
      });
      onClose();
    } catch (err: any) {
      const respData = err?.response?.data;
      if (respData?.non_field_errors) {
        setError('This holding (ticker & market) already exists in this portfolio.');
      } else {
        setError(err?.message || 'Failed to save holding. Please check parameters.');
      }
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Holding: ${holding?.ticker}` : 'Add New Holding'}
      subtitle={
        isEdit
          ? 'Update position quantity or average buy price'
          : 'Record a security position lot into this portfolio'
      }
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="holding-modal-form"
            isLoading={isLoading}
          >
            {isEdit ? 'Update Position' : 'Add Position'}
          </Button>
        </>
      }
    >
      <form id="holding-modal-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-status-negative-soft border border-status-negative/30 text-status-negative text-xs rounded-lg font-medium">
            {error}
          </div>
        )}

        {/* Ticker & Market */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <Input
              label="Ticker Symbol"
              placeholder="e.g. RELIANCE, TCS, INFY, AAPL"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={isEdit}
              required
              autoFocus={!isEdit}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1.5">
              Market
            </label>
            <select
              value={market}
              onChange={(e) => setMarket(e.target.value as 'IN' | 'US')}
              disabled={isEdit}
              className="w-full bg-surface text-text-primary text-sm rounded-lg border border-border-theme px-3 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <option value="IN">IN (India)</option>
              <option value="US">US (United States)</option>
            </select>
          </div>
        </div>

        {/* Quantity & Average Buy Price */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Quantity (Shares / Units)"
            type="number"
            step="any"
            placeholder="e.g. 10"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
          <Input
            label={`Average Buy Price (${market === 'US' ? 'USD' : 'INR'})`}
            type="number"
            step="any"
            placeholder="e.g. 2850.00"
            value={averagePrice}
            onChange={(e) => setAveragePrice(e.target.value)}
            required
          />
        </div>

        {/* Inline submit button */}
        <div className="pt-2 flex justify-end">
          <Button
            variant="primary"
            size="sm"
            type="submit"
            isLoading={isLoading}
          >
            {isEdit ? 'Update Position' : 'Add Position'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
