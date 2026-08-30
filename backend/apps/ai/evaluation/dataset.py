"""Small, stable benchmark cases without time-sensitive market facts."""

from apps.ai.evaluation.schemas import EvaluationCase


EVALUATION_DATASET: list[EvaluationCase] = [
    EvaluationCase(
        case_id="finance-revenue-profit",
        category="finance",
        question="What should a basic company financial analysis cover?",
        reference_answer="It should cover revenue, profit, and cash flow.",
        required_concepts=["revenue", "profit", "cash flow"],
    ),
    EvaluationCase(
        case_id="market-price-volatility",
        category="market",
        question="What should be considered in a basic market-price analysis?",
        reference_answer="Consider price, volume, and volatility.",
        required_concepts=["price", "volume", "volatility"],
    ),
    EvaluationCase(
        case_id="news-relevance-source",
        category="news",
        question="How should company news be assessed?",
        reference_answer="Assess the source, relevance, and recency of news.",
        required_concepts=["source", "relevance", "recency"],
    ),
    EvaluationCase(
        case_id="risk-diversification",
        category="risk",
        question="What are basic considerations in investment risk assessment?",
        reference_answer="Consider diversification, volatility, and downside risk.",
        required_concepts=["diversification", "volatility", "downside"],
    ),
    EvaluationCase(
        case_id="portfolio-allocation",
        category="portfolio",
        question="What should portfolio review include?",
        reference_answer="Review allocation, diversification, and performance.",
        required_concepts=["allocation", "diversification", "performance"],
    ),
]
