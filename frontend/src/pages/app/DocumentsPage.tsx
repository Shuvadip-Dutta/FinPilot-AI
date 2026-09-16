import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Upload,
  Search,
  Layers,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Database,
} from 'lucide-react';
import { PageHeader } from '../../components/layout/PageHeader';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { LoadingSkeleton, TableRowSkeleton } from '../../components/common/LoadingSkeleton';
import { DocumentUploadModal } from '../../components/documents/DocumentUploadModal';
import { DocumentList } from '../../components/documents/DocumentList';
import { DocumentSearchForm } from '../../components/documents/DocumentSearchForm';
import { DocumentSearchResults } from '../../components/documents/DocumentSearchResults';
import { documentsApi } from '../../api/documents';
import {
  FinancialDocument,
  DocumentSearchRequest,
  DocumentSearchResult,
} from '../../types/documents';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<FinancialDocument[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [docError, setDocError] = useState<string | null>(null);

  // Search State
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [lastQuery, setLastQuery] = useState<string>('');
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Upload Modal State
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Delete Confirmation Modal State
  const [confirmDeleteDoc, setConfirmDeleteDoc] = useState<FinancialDocument | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Load user documents
  const loadDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    setDocError(null);
    try {
      const docs = await documentsApi.getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setDocError(err?.message || 'Failed to load financial documents.');
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Handle Search
  const handleSearch = async (req: DocumentSearchRequest) => {
    setIsSearching(true);
    setSearchError(null);
    setLastQuery(req.query);
    setHasSearched(true);
    try {
      const response = await documentsApi.searchDocuments(req);
      setSearchResults(response.results || []);
    } catch (err: any) {
      setSearchError(err?.message || 'Failed to execute semantic search.');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Handle Document Upload Success
  const handleUploadSuccess = (newDoc: FinancialDocument) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
  };

  // Handle Document Deletion Trigger
  const handleDeleteClick = (id: string) => {
    const doc = documents.find((d) => d.id === id);
    if (doc) {
      setDeleteError(null);
      setConfirmDeleteDoc(doc);
    }
  };

  // Execute Document Deletion
  const handleConfirmDelete = async () => {
    if (!confirmDeleteDoc) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await documentsApi.deleteDocument(confirmDeleteDoc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== confirmDeleteDoc.id));
      // Also prune deleted document from search results
      setSearchResults((prev) => prev.filter((r) => r.document_id !== confirmDeleteDoc.id));
      setConfirmDeleteDoc(null);
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to delete document. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  // Summary Metrics
  const totalChunks = documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0);
  const completedDocs = documents.filter((d) => d.ingestion_status === 'COMPLETED').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <PageHeader
        title="Document Intelligence & RAG"
        subtitle="Upload corporate filings (10-K, 10-Q, annual reports) and research notes to inject verified ground-truth context into financial analysis agents."
        badge={<Badge variant="info">Module 11</Badge>}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadDocuments}
              disabled={isLoadingDocs}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDocs ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsUploadOpen(true)}
              className="flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload Document
            </Button>
          </div>
        }
      />

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Total Documents
            </div>
            <FileText className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-text-primary">{documents.length}</span>
            <span className="text-xs text-text-muted">
              ({completedDocs} indexed)
            </span>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Vectorized Chunks
            </div>
            <Layers className="w-4 h-4 text-status-info" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-text-primary">{totalChunks}</span>
            <span className="text-xs text-text-muted">dense embeddings in Qdrant</span>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              RAG Foundation Status
            </div>
            <Database className="w-4 h-4 text-status-success" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-sm font-semibold text-status-success flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" />
              Active & Isolated
            </span>
            <span className="text-xs text-text-muted">user-scoped tenant filter</span>
          </div>
        </Card>
      </div>

      {/* Semantic Search Section */}
      <Card className="p-5">
        <div className="mb-4">
          <h2 className="text-base font-bold text-text-primary flex items-center gap-2">
            <Search className="w-4 h-4 text-accent-primary" />
            Semantic Corpus Search
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Query across vectorized documents using dense cosine-similarity retrieval.
          </p>
        </div>

        <DocumentSearchForm onSearch={handleSearch} isLoading={isSearching} />

        {searchError && (
          <div className="mt-4 p-3 bg-status-danger-soft border border-status-danger/30 rounded-lg flex items-start gap-2 text-xs text-status-danger">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>{searchError}</div>
          </div>
        )}

        <div className="mt-6 pt-5 border-t border-border-subtle">
          <DocumentSearchResults
            results={searchResults}
            query={lastQuery}
            hasSearched={hasSearched}
          />
        </div>
      </Card>

      {/* Document Library Section */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-text-primary flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent-primary" />
              Document Library
            </h2>
            <p className="text-xs text-text-muted mt-0.5">
              Manage uploaded filings and inspect per-document vector ingestion status.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload
          </Button>
        </div>

        {docError && (
          <div className="mb-4 p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>{docError}</div>
          </div>
        )}

        {isLoadingDocs ? (
          <div className="p-4 space-y-3">
            <TableRowSkeleton columns={6} />
            <TableRowSkeleton columns={6} />
            <TableRowSkeleton columns={6} />
          </div>
        ) : (
          <DocumentList
            documents={documents}
            onDelete={handleDeleteClick}
            isDeletingId={isDeleting ? confirmDeleteDoc?.id : null}
            onOpenUpload={() => setIsUploadOpen(true)}
          />
        )}
      </Card>

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={confirmDeleteDoc !== null}
        onClose={() => !isDeleting && setConfirmDeleteDoc(null)}
        title="Delete Document"
        subtitle="This action cannot be undone."
        maxWidth="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Are you sure you want to permanently delete{' '}
            <span className="font-semibold text-white">
              {confirmDeleteDoc?.filename}
            </span>{' '}
            and its vector embeddings?
          </p>

          {deleteError && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg flex items-start gap-2 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>{deleteError}</div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmDeleteDoc(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleConfirmDelete}
              isLoading={isDeleting}
              disabled={isDeleting}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

