/**
 * Type definitions for Financial Document RAG Intelligence.
 */

export type DocumentIngestionStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface FinancialDocument {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  ticker?: string | null;
  market?: string | null;
  ingestion_status: DocumentIngestionStatus;
  chunk_count: number;
  ingestion_error?: string | null;
  created_at: string;
}

export interface DocumentUploadPayload {
  file: File;
  ticker?: string;
  market?: string;
}

export interface DocumentSearchRequest {
  query: string;
  top_k?: number;
  ticker?: string;
  market?: string;
}

export interface DocumentSearchResult {
  text: string;
  score: number;
  document_id: string;
  chunk_id: string;
  document_name: string;
  ticker?: string | null;
  market?: string | null;
  page_start?: number;
  page_count?: number;
  metadata?: Record<string, any>;
}

export interface DocumentSearchResponse {
  results: DocumentSearchResult[];
  count: number;
  query: string;
}
