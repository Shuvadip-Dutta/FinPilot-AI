import React, { useState } from 'react';
import { ChatMessage } from '../../types/research';
import { MarkdownContent } from './MarkdownContent';
import { EvidencePanel } from './EvidencePanel';
import { ProvenancePanel } from './ProvenancePanel';
import { Badge } from '../common/Badge';
import {
  Sparkles,
  User,
  Copy,
  Check,
  BookOpen,
  GitCommit,
  TrendingUp,
  Clock,
} from 'lucide-react';
import { formatDate } from '../../utils/formatters';

interface AiResponseViewProps {
  message: ChatMessage;
}

export const AiResponseView: React.FC<AiResponseViewProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showProvenance, setShowProvenance] = useState(false);

  const isUser = message.role === 'user';
  const hasEvidence = Boolean(message.evidence && message.evidence.length > 0);
  const hasProvenance = Boolean(message.provenance);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard write failure
    }
  };

  // Sentiment formatting
  const sentimentStr =
    typeof message.sentiment === 'string'
      ? message.sentiment
      : message.sentiment?.label;

  const sentimentVariant =
    sentimentStr?.toLowerCase().includes('bull') || sentimentStr?.toLowerCase().includes('pos')
      ? 'success'
      : sentimentStr?.toLowerCase().includes('bear') || sentimentStr?.toLowerCase().includes('neg')
      ? 'danger'
      : 'neutral';

  return (
    <div
      className={`rounded-2xl transition-all ${
        isUser
          ? 'bg-surface-secondary/70 border border-border-theme p-4 sm:p-5 ml-auto max-w-3xl'
          : 'bg-surface border border-border-theme p-5 sm:p-6 shadow-card'
      }`}
    >
      {/* Header Bar: Role, Ticker, Timestamp, Actions */}
      <div className="flex items-center justify-between gap-3 mb-3 pb-2.5 border-b border-border-subtle flex-wrap">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
              isUser
                ? 'bg-surface-secondary text-text-muted'
                : 'bg-accent-primary text-white font-bold'
            }`}
          >
            {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4 stroke-[2.5]" />}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-text-primary">
              {isUser ? 'Analyst' : 'FinPilot AI'}
            </span>
            {!isUser && (
              <Badge variant="info" size="sm" className="font-mono text-[10px]">
                LangGraph Synthesizer
              </Badge>
            )}
            {message.ticker && (
              <Badge variant="neutral" size="sm" className="font-mono text-[10px]">
                {message.ticker} {message.market ? `(${message.market})` : ''}
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {sentimentStr && (
            <Badge variant={sentimentVariant} size="sm" className="font-mono text-[10px]">
              <TrendingUp className="w-3 h-3 mr-1 inline" />
              {sentimentStr}
            </Badge>
          )}

          <span className="text-[11px] text-text-muted font-mono flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(message.timestamp, { includeTime: true })}
          </span>

          {!isUser && (
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-secondary transition-colors cursor-pointer"
              title="Copy markdown text"
              aria-label="Copy markdown text"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-status-success" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      </div>

      {/* Main Content Body */}
      {isUser ? (
        <p className="text-sm text-text-primary leading-relaxed font-sans whitespace-pre-wrap">
          {message.content}
        </p>
      ) : (
        <MarkdownContent content={message.content} />
      )}

      {/* Auxiliary Panels Toggle Bar (Evidence & Provenance) */}
      {!isUser && (hasEvidence || hasProvenance) && (
        <div className="mt-4 pt-3 border-t border-border-subtle flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {hasEvidence && (
              <button
                type="button"
                onClick={() => setShowEvidence(!showEvidence)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium font-mono flex items-center gap-1.5 transition-all cursor-pointer ${
                  showEvidence
                    ? 'bg-accent-soft text-accent-primary border border-accent-primary/30 font-semibold'
                    : 'bg-surface-secondary text-text-muted hover:text-text-primary border border-border-subtle'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Evidence ({message.evidence?.length || 0})</span>
              </button>
            )}

            {hasProvenance && (
              <button
                type="button"
                onClick={() => setShowProvenance(!showProvenance)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium font-mono flex items-center gap-1.5 transition-all cursor-pointer ${
                  showProvenance
                    ? 'bg-status-info-soft text-status-info border border-status-info/30 font-semibold'
                    : 'bg-surface-secondary text-text-muted hover:text-text-primary border border-border-subtle'
                }`}
              >
                <GitCommit className="w-3.5 h-3.5" />
                <span>Provenance Trace</span>
              </button>
            )}
          </div>

          <span className="text-[11px] text-slate-500 font-mono">
            Ground truth verified via RAG
          </span>
        </div>
      )}

      {/* Collapsible Evidence Panel */}
      {showEvidence && hasEvidence && (
        <div className="mt-4 animate-in fade-in slide-in-from-top-2">
          <EvidencePanel evidence={message.evidence} />
        </div>
      )}

      {/* Collapsible Provenance Panel */}
      {showProvenance && hasProvenance && (
        <div className="mt-4 animate-in fade-in slide-in-from-top-2">
          <ProvenancePanel provenance={message.provenance} />
        </div>
      )}
    </div>
  );
};
