import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { DocumentSearchRequest } from '../../types/documents';

interface DocumentSearchFormProps {
  onSearch: (request: DocumentSearchRequest) => void;
  isLoading: boolean;
}

export const DocumentSearchForm: React.FC<DocumentSearchFormProps> = ({
  onSearch,
  isLoading,
}) => {
  const [query, setQuery] = useState('');
  const [ticker, setTicker] = useState('');
  const [topK, setTopK] = useState(5);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    onSearch({
      query: query.trim(),
      ticker: ticker.trim() || undefined,
      top_k: topK,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search Query Input */}
        <div className="flex-1 relative">
          <Input
            placeholder="Search financial facts, revenue segments, management discussion, risks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            className="pl-10"
          />
          <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Ticker Filter */}
        <div className="w-full sm:w-36">
          <Input
            placeholder="Ticker filter"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            disabled={isLoading}
          />
        </div>

        {/* Top K Selector */}
        <div className="w-full sm:w-28">
          <select
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            disabled={isLoading}
            className="w-full bg-surface border border-border-theme rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5</option>
            <option value={8}>Top 8</option>
            <option value={10}>Top 10</option>
          </select>
        </div>

        {/* Search Action */}
        <Button
          type="submit"
          variant="primary"
          disabled={!query.trim() || isLoading}
          className="flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Search Corpus
            </>
          )}
        </Button>
      </div>
    </form>
  );
};
