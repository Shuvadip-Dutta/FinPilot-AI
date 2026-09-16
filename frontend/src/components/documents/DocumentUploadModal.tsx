import React, { useState, useRef } from 'react';
import { Upload, FileText, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { documentsApi } from '../../api/documents';
import { FinancialDocument } from '../../types/documents';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (doc: FinancialDocument) => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [ticker, setTicker] = useState('');
  const [market, setMarket] = useState('IN');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetForm = () => {
    setFile(null);
    setTicker('');
    setMarket('IN');
    setError(null);
    setSuccess(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      resetForm();
      onClose();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setSuccess(null);
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Validate size (10 MB max)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File exceeds maximum allowed size of 10 MB.');
      return;
    }

    // Validate extension
    const name = selectedFile.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.txt')) {
      setError('Invalid file format. Only PDF and TXT documents are supported.');
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setError(null);
    const droppedFile = e.dataTransfer.files?.[0];
    if (!droppedFile) return;

    if (droppedFile.size > 10 * 1024 * 1024) {
      setError('File exceeds maximum allowed size of 10 MB.');
      return;
    }

    const name = droppedFile.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.txt')) {
      setError('Invalid file format. Only PDF and TXT documents are supported.');
      return;
    }

    setFile(droppedFile);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a document to upload.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const doc = await documentsApi.uploadDocument({
        file,
        ticker: ticker.trim() || undefined,
        market: market.trim() || undefined,
      });

      setSuccess(`Document "${doc.filename}" successfully vectorized (${doc.chunk_count} chunks).`);
      setTimeout(() => {
        onUploadSuccess(doc);
        handleClose();
      }, 1200);
    } catch (err: any) {
      const message = err?.message || err?.detail || 'Failed to upload and ingest document.';
      setError(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Financial Document"
      subtitle="Index 10-K filings, annual reports, quarterly disclosures, or research notes for RAG intelligence."
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-950/50 border border-rose-800/80 rounded-lg flex items-start gap-2 text-sm text-rose-300">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {success && (
          <div className="p-3 bg-emerald-950/50 border border-emerald-800/80 rounded-lg flex items-start gap-2 text-sm text-emerald-300">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="flex-1">{success}</div>
          </div>
        )}

        {/* Drag & Drop File Upload Area */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            file
              ? 'border-accent-primary bg-accent-soft/30'
              : 'border-border-theme hover:border-accent-primary/40 bg-surface-secondary/40 hover:bg-surface-secondary/70'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,text/plain,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="flex flex-col items-center justify-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-accent-soft flex items-center justify-center text-accent-primary">
              {file ? <FileText className="w-6 h-6" /> : <Upload className="w-6 h-6" />}
            </div>
            {file ? (
              <div>
                <p className="text-sm font-medium text-text-primary">{file.name}</p>
                <p className="text-xs text-text-muted">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.type || 'text/document'}
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-text-primary">
                  Click to browse or drag and drop your file here
                </p>
                <p className="text-xs text-text-muted">PDF or UTF-8 TXT (Max 10 MB)</p>
              </div>
            )}
          </div>
        </div>

        {/* Optional Metadata */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Associated Ticker (Optional)
            </label>
            <Input
              placeholder="e.g. INFY, AAPL"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={isUploading}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Market (Optional)
            </label>
            <select
              value={market}
              onChange={(e) => setMarket(e.target.value)}
              disabled={isUploading}
              className="w-full bg-surface border border-border-theme rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-hidden focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/30"
            >
              <option value="IN">IN (India / NSE / BSE)</option>
              <option value="US">US (United States / NYSE / NASDAQ)</option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-border-theme">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isUploading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={!file || isUploading}
            className="flex items-center gap-2"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Ingesting & Vectorizing...
              </>
            ) : (
              'Upload & Ingest'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
