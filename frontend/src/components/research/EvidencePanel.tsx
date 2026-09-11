import React, { useState } from 'react';
import { EvidenceItem } from '../../types/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  FileText,
  ExternalLink,
  Search,
  BookOpen,
  Calendar,
  Layers,
  Sparkles,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

interface EvidencePanelProps {
  evidence?: EvidenceItem[];
  title?: string;
  className?: string;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence = [],
  title = 'Research Evidence & Citations',
  className = '',
}) => {
  const [filterText, setFilterText] = useState('');

  const filteredEvidence = evidence.filter((item) => {
    if (!filterText.trim()) return true;
    const query = filterText.toLowerCase();
    return (
      (item.title && item.title.toLowerCase().includes(query)) ||
      (item.snippet && item.snippet.toLowerCase().includes(query)) ||
      (item.content && item.content.toLowerCase().includes(query)) ||
      (item.source && item.source.toLowerCase().includes(query))
    );
  });

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-cyan-400" />
          <span>{title}</span>
          <Badge variant="info" size="sm">
            {evidence.length} {evidence.length === 1 ? 'source' : 'sources'}
          </Badge>
        </div>
      }
      subtitle="Verifiable sources, regulatory filings, and RAG documents referenced by the AI"
      className={className}
    >
      {/* Evidence search filter */}
      {evidence.length > 2 && (
        <div className="mb-4 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter evidence by title, text, or source..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      )}

      {evidence.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs flex flex-col items-center">
          <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-2">
            <FileText className="w-5 h-5" />
          </div>
          <p className="font-medium text-slate-300">No citations attached</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Evidence and regulatory excerpts will appear here once synthesized by LangGraph RAG.
          </p>
        </div>
      ) : filteredEvidence.length === 0 ? (
        <div className="py-6 text-center text-slate-400 text-xs">
          No citations match &ldquo;{filterText}&rdquo;
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
          {filteredEvidence.map((item, index) => {
            const itemTitle = item.title || `Evidence Document #${index + 1}`;
            const itemSnippet = item.snippet || item.content || '';
            const itemDate = item.published_date || item.published_at || item.date;
            const score = item.score ?? item.confidence ?? item.relevance;

            return (
              <div
                key={item.id ?? `evidence-${index}`}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all text-xs"
              >
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
                      {item.source_type || 'RAG'}
                    </Badge>
                    <span className="font-semibold text-slate-200 line-clamp-1">
                      {itemTitle}
                    </span>
                  </div>

                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 shrink-0 transition-colors"
                      title="Open source document"
                    >
                      <span className="text-[11px]">View</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>

                {itemSnippet && (
                  <p className="text-slate-400 leading-relaxed line-clamp-3 my-2 font-serif text-[11.5px] bg-slate-900/50 p-2 rounded border border-slate-800/40">
                    &ldquo;{itemSnippet}&rdquo;
                  </p>
                )}

                <div className="flex items-center justify-between text-[10.5px] text-slate-500 font-mono mt-2 pt-2 border-t border-slate-900">
                  <span className="flex items-center gap-1 text-slate-400">
                    <Layers className="w-3 h-3 text-cyan-400/70" />
                    {item.source || 'Knowledge Store'}
                  </span>

                  <div className="flex items-center gap-3">
                    {itemDate && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(itemDate)}
                      </span>
                    )}

                    {score !== undefined && (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <Sparkles className="w-3 h-3" />
                        Score: {(score > 1 ? score : score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
