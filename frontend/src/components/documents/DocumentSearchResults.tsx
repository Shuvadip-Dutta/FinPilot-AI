import React from 'react';
import { FileText, Sparkles, HelpCircle, BookOpen } from 'lucide-react';
import { DocumentSearchResult } from '../../types/documents';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';

interface DocumentSearchResultsProps {
  results: DocumentSearchResult[];
  query?: string;
  hasSearched: boolean;
}

export const DocumentSearchResults: React.FC<DocumentSearchResultsProps> = ({
  results,
  query,
  hasSearched,
}) => {
  if (!hasSearched) {
    return (
      <div className="py-12 text-center text-slate-400">
        <BookOpen className="w-10 h-10 text-slate-600 mx-auto mb-3" />
        <p className="text-sm font-medium text-slate-300">Semantic Document Retrieval</p>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          Enter a semantic financial query above to search through all your indexed PDFs and text documents using dense embeddings.
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="py-12 text-center text-slate-400 bg-slate-900/30 rounded-xl border border-slate-800/60 p-6">
        <HelpCircle className="w-10 h-10 text-amber-500/70 mx-auto mb-3" />
        <p className="text-sm font-medium text-slate-200">No Matching Chunks Found</p>
        <p className="text-xs text-slate-400 mt-1">
          No document passages scored sufficiently high for &ldquo;{query}&rdquo;. Try broadening your keywords or uploading additional relevant filings.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-text-muted px-1">
        <span>
          Found <strong className="text-accent-primary">{results.length}</strong> relevant chunk{results.length > 1 ? 's' : ''} for &ldquo;{query}&rdquo;
        </span>
        <span className="font-mono text-[11px] text-text-muted">Ranked by Cosine Similarity</span>
      </div>

      <div className="space-y-3">
        {results.map((result, idx) => {
          const scorePercent = (Math.max(0, Math.min(1, result.score)) * 100).toFixed(1);
          const pageDisplay = result.page_start || result.metadata?.page || 1;

          return (
            <Card
              key={`${result.chunk_id}-${idx}`}
              className="p-4 border-border-theme bg-surface hover:border-accent-primary/40 transition-all shadow-card"
            >
              {/* Provenance Header */}
              <div className="flex items-center justify-between gap-2 mb-2.5 pb-2 border-b border-border-theme">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 font-medium text-xs text-text-primary">
                    <FileText className="w-3.5 h-3.5 text-accent-primary" />
                    <span>{result.document_name}</span>
                  </div>

                  {result.ticker && (
                    <Badge variant="info" size="sm" className="font-mono">
                      {result.ticker}
                    </Badge>
                  )}

                  {result.market && (
                    <Badge variant="neutral" size="sm" className="font-mono">
                      {result.market}
                    </Badge>
                  )}

                  <Badge variant="neutral" size="sm" className="font-mono text-text-muted">
                    Page {pageDisplay}
                  </Badge>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <Badge
                    variant={result.score >= 0.75 ? 'success' : result.score >= 0.5 ? 'info' : 'warning'}
                    className="font-mono text-[11px] flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3" />
                    {scorePercent}% match ({result.score.toFixed(3)})
                  </Badge>
                </div>
              </div>

              {/* Chunk Snippet Text */}
              <div className="text-xs text-text-primary leading-relaxed font-sans whitespace-pre-wrap bg-surface-secondary/50 p-3 rounded-lg border border-border-theme font-mono">
                {result.text}
              </div>

              {/* Metadata Provenance Footer */}
              <div className="flex items-center justify-between text-[11px] text-text-muted mt-2 font-mono">
                <span>Chunk ID: {result.chunk_id}</span>
                <span>Doc ID: {result.document_id.slice(0, 8)}...</span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
