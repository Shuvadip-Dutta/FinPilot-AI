import { apiClient } from './client';
import {
  FinancialDocument,
  DocumentUploadPayload,
  DocumentSearchRequest,
  DocumentSearchResponse,
} from '../types/documents';

export const documentsApi = {
  /**
   * GET /api/v1/research/documents/
   * List all documents owned by the authenticated user
   */
  async getDocuments(): Promise<FinancialDocument[]> {
    return apiClient.get<FinancialDocument[]>('research/documents/');
  },

  /**
   * POST /api/v1/research/documents/
   * Upload and ingest a financial document
   */
  async uploadDocument(payload: DocumentUploadPayload): Promise<FinancialDocument> {
    const formData = new FormData();
    formData.append('file', payload.file);
    if (payload.ticker) {
      formData.append('ticker', payload.ticker.trim().toUpperCase());
    }
    if (payload.market) {
      formData.append('market', payload.market.trim().toUpperCase());
    }

    return apiClient.post<FinancialDocument>('research/documents/', formData);
  },

  /**
   * POST /api/v1/research/documents/search/
   * Semantic vector search across user's documents
   */
  async searchDocuments(payload: DocumentSearchRequest): Promise<DocumentSearchResponse> {
    return apiClient.post<DocumentSearchResponse>('research/documents/search/', payload);
  },

  /**
   * DELETE /api/v1/research/documents/<id>/
   * Delete document, vector chunks, and source file
   */
  async deleteDocument(documentId: string): Promise<void> {
    return apiClient.delete<void>(`research/documents/${documentId}/`);
  },
};
