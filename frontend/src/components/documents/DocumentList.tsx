import React from 'react';
import { FileText, Trash2, Layers, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { FinancialDocument, DocumentIngestionStatus } from '../../types/documents';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { EmptyState } from '../common/EmptyState';

interface DocumentListProps {
  documents: FinancialDocument[];
  onDelete: (id: string) => void;
  isDeletingId?: string | null;
  onOpenUpload: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  onDelete,
  isDeletingId,
  onOpenUpload,
}) => {
  if (documents.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No Financial Documents Indexed"
        description="Upload corporate disclosures, earnings reports, or 10-K filings to empower the Financial Analysis Agent with localized RAG intelligence."
        actionLabel="Upload First Document"
        onAction={onOpenUpload}
      />
    );
  }

  const getStatusBadge = (status: DocumentIngestionStatus) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <Badge variant="success" dot className="flex items-center gap-1 font-mono">
            <CheckCircle2 className="w-3 h-3" />
            COMPLETED
          </Badge>
        );
      case 'PROCESSING':
        return (
          <Badge variant="info" dot className="flex items-center gap-1 font-mono animate-pulse">
            <Clock className="w-3 h-3" />
            PROCESSING
          </Badge>
        );
      case 'PENDING':
        return (
          <Badge variant="warning" dot className="flex items-center gap-1 font-mono">
            <Clock className="w-3 h-3" />
            PENDING
          </Badge>
        );
      case 'FAILED':
        return (
          <Badge variant="danger" dot className="flex items-center gap-1 font-mono">
            <AlertTriangle className="w-3 h-3" />
            FAILED
          </Badge>
        );
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDate = (dateStr: string): string => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider bg-slate-950/40">
            <th className="py-3 px-4">Document</th>
            <th className="py-3 px-4">Metadata</th>
            <th className="py-3 px-4">Status</th>
            <th className="py-3 px-4">Vector Chunks</th>
            <th className="py-3 px-4">Indexed Date</th>
            <th className="py-3 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {documents.map((doc) => {
            const isDeleting = isDeletingId === doc.id;
            return (
              <tr
                key={doc.id}
                className="hover:bg-slate-900/40 transition-colors group"
              >
                <td className="py-3.5 px-4 font-medium text-white flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-cyan-950/40 border border-cyan-800/40 flex items-center justify-center text-cyan-400 shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="truncate max-w-xs">
                    <div className="font-semibold text-slate-200 truncate" title={doc.filename}>
                      {doc.filename}
                    </div>
                    <div className="text-xs text-slate-400">
                      {formatFileSize(doc.file_size)} • {doc.content_type || 'document'}
                    </div>
                    {doc.ingestion_error && (
                      <div className="text-xs text-rose-400 mt-0.5 truncate" title={doc.ingestion_error}>
                        Error: {doc.ingestion_error}
                      </div>
                    )}
                  </div>
                </td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {doc.ticker ? (
                      <Badge variant="info" className="font-mono">
                        {doc.ticker}
                      </Badge>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                    {doc.market && (
                      <Badge variant="neutral" className="font-mono">
                        {doc.market}
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="py-3.5 px-4">{getStatusBadge(doc.ingestion_status)}</td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-1 text-slate-300 font-mono text-xs">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{doc.chunk_count} chunks</span>
                  </div>
                </td>
                <td className="py-3.5 px-4 text-xs text-slate-400">
                  {formatDate(doc.created_at)}
                </td>
                <td className="py-3.5 px-4 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(doc.id)}
                    disabled={isDeleting}
                    className="text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
                    title="Delete document and vector points"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
