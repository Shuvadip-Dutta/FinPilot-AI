"""API views for financial document management and RAG search."""

import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services.rag_tools import search_financial_documents
from apps.research.document_serializers import (
    DocumentSearchSerializer,
    DocumentUploadSerializer,
    FinancialDocumentSerializer,
)
from apps.research.document_service import DocumentIngestionService
from apps.research.models import FinancialDocument

logger = logging.getLogger("finpilot")


class FinancialDocumentListCreateView(APIView):
    """List current user's documents or upload a new financial document."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = FinancialDocument.objects.filter(user=request.user).order_by("-created_at")
        serializer = FinancialDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data["file"]
        ticker = serializer.validated_data.get("ticker")
        market = serializer.validated_data.get("market")

        try:
            doc = DocumentIngestionService.ingest_document(
                user=request.user,
                file=uploaded_file,
                ticker=ticker,
                market=market,
            )
            response_serializer = FinancialDocumentSerializer(doc)
            if doc.ingestion_status == FinancialDocument.STATUS_COMPLETED:
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {
                        "error": doc.ingestion_error or "Ingestion failed.",
                        "document": response_serializer.data,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as exc:
            logger.exception("Document ingestion failed: %s", exc)
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FinancialDocumentSearchView(APIView):
    """Search vectorized documents scoped to the authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        top_k = serializer.validated_data.get("top_k", 5)
        ticker = serializer.validated_data.get("ticker")
        market = serializer.validated_data.get("market")

        try:
            raw_results = search_financial_documents(
                query=query,
                ticker=ticker,
                market=market,
                top_k=top_k,
                user_id=request.user.id,
            )

            doc_items = raw_results.get("documents", [])
            formatted_results = []

            for item in doc_items:
                metadata = item.get("metadata", {}) or {}
                formatted_results.append(
                    {
                        "text": item.get("text", ""),
                        "score": item.get("score", 0.0),
                        "document_id": item.get("document_id", ""),
                        "chunk_id": item.get("chunk_id", ""),
                        "document_name": metadata.get("document_name") or metadata.get("filename") or "Document",
                        "ticker": metadata.get("ticker") or None,
                        "market": metadata.get("market") or None,
                        "page_start": metadata.get("page_start", 1),
                        "page_count": metadata.get("page_count", 1),
                        "metadata": metadata,
                    }
                )

            return Response(
                {
                    "results": formatted_results,
                    "count": len(formatted_results),
                    "query": query,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Document search failed: %s", exc)
            return Response(
                {"error": f"Search failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FinancialDocumentDetailView(APIView):
    """Retrieve or delete a specific financial document owned by the user."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        deleted = DocumentIngestionService.delete_document(
            user=request.user,
            document_id=document_id,
        )
        if not deleted:
            return Response(
                {"error": "Document not found or not authorized."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
