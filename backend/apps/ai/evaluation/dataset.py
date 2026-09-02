"""Small, stable benchmark cases without time-sensitive market facts."""

from apps.ai.evaluation.schemas import EvaluationCase
from apps.ai.services.llm_service import ModelTier


ARCHITECTURE_TIER_MAP: dict[str, ModelTier] = {
    "finance": ModelTier.REASONING,
    "market": ModelTier.FAST,
    "news": ModelTier.FAST,
    "risk": ModelTier.REASONING,
    "portfolio": ModelTier.REASONING,
}


def validate_category_tier_mapping() -> bool:
    """Verify that the explicitly defined architecture matches the current model assignments."""
    return all(
        case.expected_tier == ARCHITECTURE_TIER_MAP[case.category]
        for case in EVALUATION_DATASET
    )


EVALUATION_DATASET: list[EvaluationCase] = [
    EvaluationCase(
        case_id="finance-revenue-profit",
        category="finance",
        question="What should a basic company financial analysis cover?",
        reference_answer="It should cover revenue, profit, and cash flow.",
        required_concepts=["revenue", "profit", "cash flow"],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-price-volatility",
        category="market",
        question="What should be considered in a basic market-price analysis?",
        reference_answer="Consider price, volume, and volatility.",
        required_concepts=["price", "volume", "volatility"],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-relevance-source",
        category="news",
        question="How should company news be assessed?",
        reference_answer="Assess the source, relevance, and recency of news.",
        required_concepts=["source", "relevance", "recency"],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-diversification",
        category="risk",
        question="What are basic considerations in investment risk assessment?",
        reference_answer="Consider diversification, volatility, and downside risk.",
        required_concepts=["diversification", "volatility", "downside"],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-allocation",
        category="portfolio",
        question="What should portfolio review include?",
        reference_answer="Review allocation, diversification, and performance.",
        required_concepts=["allocation", "diversification", "performance"],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
]
