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
  const [market, setMarket] = useState('NSE');
  const [quantity, setQuantity] = useState('');
  const [buyPrice, setBuyPrice] = useState('');
  const [buyDate, setBuyDate] = useState('');
  const [sector, setSector] = useState('');
  const [assetClass, setAssetClass] = useState('Equity');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (holding) {
      setTicker(holding.ticker || holding.symbol || '');
      setMarket(holding.market || 'NSE');
      const qty = holding.quantity ?? holding.shares ?? '';
      setQuantity(String(qty));
      const price = holding.buy_price ?? holding.average_buy_price ?? holding.avg_price ?? '';
      setBuyPrice(String(price));
      setBuyDate(holding.buy_date || holding.purchase_date || '');
      setSector(holding.sector || '');
      setAssetClass(holding.asset_class || 'Equity');
      setNotes(holding.notes || '');
      setError(null);
    } else {
      // Defaults for new holding
      setTicker('');
      setMarket(currency === 'USD' ? 'NASDAQ' : 'NSE');
      setQuantity('');
      setBuyPrice('');
      setBuyDate(new Date().toISOString().split('T')[0]);
      setSector('');
      setAssetClass('Equity');
      setNotes('');
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

    const parsedPrice = parseFloat(buyPrice);
    if (isNaN(parsedPrice) || parsedPrice <= 0) {
      setError('Please enter a valid buy price greater than 0');
      return;
    }

    setError(null);
    try {
      await onSubmit({
        ticker: ticker.trim().toUpperCase(),
        market,
        quantity: parsedQty,
        buy_price: parsedPrice,
        buy_date: buyDate || undefined,
        sector: sector.trim() || undefined,
        asset_class: assetClass || undefined,
        notes: notes.trim() || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to save holding. Please check parameters.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Holding: ${holding?.ticker}` : 'Add New Holding'}
      subtitle={
        isEdit
          ? 'Update purchase lot details, position quantity, or cost basis'
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
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            {isEdit ? 'Update Position' : 'Add Position'}
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

        {/* Ticker & Market */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <Input
              label="Ticker Symbol"
              placeholder="e.g. RELIANCE, TCS, INFY, AAPL"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={isEdit} // Ticker is typically fixed when editing a holding
              required
              autoFocus={!isEdit}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
              Market
            </label>
            <select
              value={market}
              onChange={(e) => setMarket(e.target.value)}
              className="w-full bg-slate-900/90 text-slate-100 text-sm rounded-lg border border-slate-700/80 px-3 py-2 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="NSE">NSE</option>
              <option value="BSE">BSE</option>
              <option value="NASDAQ">NASDAQ</option>
              <option value="NYSE">NYSE</option>
            </select>
          </div>
        </div>

        {/* Quantity & Buy Price */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Quantity (Shares / Units)"
            type="number"
            step="any"
            placeholder="e.g. 50"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
          />
          <Input
            label={`Average Buy Price (${currency})`}
            type="number"
            step="any"
            placeholder="e.g. 2450.50"
            value={buyPrice}
            onChange={(e) => setBuyPrice(e.target.value)}
            required
          />
        </div>

        {/* Buy Date & Asset Class */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Acquisition Date"
            type="date"
            value={buyDate}
            onChange={(e) => setBuyDate(e.target.value)}
          />
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
              Asset Class
            </label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value)}
              className="w-full bg-slate-900/90 text-slate-100 text-sm rounded-lg border border-slate-700/80 px-3 py-2 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="Equity">Equity (Stock)</option>
              <option value="ETF">ETF (Exchange Traded Fund)</option>
              <option value="Mutual Fund">Mutual Fund</option>
              <option value="Fixed Income">Fixed Income / Bond</option>
              <option value="Crypto">Cryptocurrency</option>
              <option value="Commodity">Commodity / Gold</option>
            </select>
          </div>
        </div>

        {/* Sector & Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Sector (Optional)"
            placeholder="e.g. Information Technology, Energy"
            value={sector}
            onChange={(e) => setSector(e.target.value)}
          />
          <Input
            label="Investment Notes (Optional)"
            placeholder="Target thesis, stop loss, rationale"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
      </form>
    </Modal>
  );
};
