from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from dataclasses import asdict
from apps.research.serializers import CompanyResearchQuerySerializer
from apps.research.services.research_service import ResearchService
from apps.research.services.symbols import Market
import requests

class CompanyResearchView(APIView):

    def get(self, request):

        serializer = CompanyResearchQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        ticker = serializer.validated_data["ticker"].upper()
        market = Market(
            serializer.validated_data["market"]
        )

        service = ResearchService()

        try:
            profile = service.get_company_profile(
                ticker,
                market,
            )

            market_data = service.get_market_data(
                ticker,
                market,
            )

        except ValueError as exc:
            return Response(
                {
                    "error": str(exc),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except requests.RequestException:
            return Response(
                {
                    "error": "External market data provider is unavailable."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "ticker": ticker,
                "market": market,
                "company": {
                    "ticker": profile.ticker,
                    "name": profile.name,
                    "exchange": profile.exchange,
                    "country": profile.country,
                    "sector": profile.sector,
                    "industry": profile.industry,
                    "description": profile.description,
                    "isin": profile.isin,
                    "nse_symbol": profile.nse_symbol,
                    "bse_code": profile.bse_code,
                },
                "market_data": (
                    [asdict(item) for item in market_data]
                    if isinstance(market_data, list)
                    else asdict(market_data)
                ),
            }
        )
        
class FinancialResearchView(APIView):

    def get(self, request):

        serializer = CompanyResearchQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        ticker = serializer.validated_data["ticker"].upper()
        market = Market(
            serializer.validated_data["market"]
        )

        service = ResearchService()

        try:
            financials = service.get_financials(
                ticker,
                market,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        except requests.RequestException as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "ticker": ticker,
                "market": market,
                "financials": [
                    {
                        "statement_type": statement.statement_type,
                        "fiscal_year": statement.fiscal_year,
                        "end_date": statement.end_date,
                        "period_type": statement.period_type,
                        "period_length": statement.period_length,
                        "metrics": [
                            {
                                "name": metric.name,
                                "key": metric.key,
                                "value": metric.value,
                            }
                            for metric in statement.metrics
                        ],
                    }
                    for statement in financials
                ],
            }
        )    
        
class KeyMetricsResearchView(APIView):

    def get(self, request):

        serializer = CompanyResearchQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        ticker = serializer.validated_data["ticker"].upper()
        market = Market(
            serializer.validated_data["market"]
        )

        service = ResearchService()

        try:
            key_metrics = service.get_key_metrics(
                ticker,
                market,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        except requests.RequestException as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "ticker": ticker,
                "market": market,
                "metrics": [
                    {
                        "category": metric.category,
                        "name": metric.name,
                        "key": metric.key,
                        "value": metric.value,
                        "raw_value": metric.raw_value,
                    }
                    for metric in key_metrics.metrics
                ],
            }
        )
        
class NewsResearchView(APIView):

    def get(self, request):

        serializer = CompanyResearchQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        ticker = serializer.validated_data["ticker"].upper()

        market = Market(
            serializer.validated_data["market"]
        )

        service = ResearchService()

        try:
            research = service.get_news(
                ticker,
                market,
            )

        except requests.RequestException:
            return Response(
                {
                    "error": "External market data provider is unavailable.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception as exc:
            return Response(
                {
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "ticker": research.ticker,
                "articles": [
                    {
                        "title": article.title,
                        "summary": article.summary,
                        "url": article.url,
                        "source": article.source,
                        "published_at": article.published_at,
                        "image_url": article.image_url,
                        "relevance_score": article.relevance_score,
                        "target_match_score": article.target_match_score,
                        "relevance_type": article.relevance_type,
                        "entities": [
                            {
                                "symbol": entity.symbol,
                                "name": entity.name,
                                "country": entity.country,
                                "entity_type": entity.entity_type,
                                "match_score": entity.match_score,
                                "sentiment_score": entity.sentiment_score,
                            }
                            for entity in article.entities or []
                        ],
                    }
                    for article in research.articles
                ],
            }
        )

class HistoricalResearchView(APIView):

    def get(self, request):

        serializer = CompanyResearchQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        ticker = serializer.validated_data["ticker"].upper()

        market = Market(
            serializer.validated_data["market"]
        )

        to_date = request.query_params.get("to_date")
        from_date = request.query_params.get("from_date")

        if not to_date:
            return Response(
                {
                    "error": "to_date is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ResearchService()

        try:
            historical = service.get_historical_data(
                ticker,
                to_date=to_date,
                from_date=from_date,
                market=market,
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        except requests.RequestException:
            return Response(
                {
                    "error": "External market data provider is unavailable.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "ticker": historical.ticker,
                "market": market,
                "candles": [
                    {
                        "timestamp": candle.timestamp,
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                        "volume": candle.volume,
                        "open_interest": candle.open_interest,
                    }
                    for candle in historical.candles
                ],
            }
        )
