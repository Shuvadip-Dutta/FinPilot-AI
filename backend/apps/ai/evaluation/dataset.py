"""Small, stable benchmark cases without time-sensitive market facts."""

from apps.ai.evaluation.schemas import EvaluationCase
from apps.ai.services.llm_service import ModelTier


ARCHITECTURE_TIER_MAP: dict[str, ModelTier] = {
    "finance": ModelTier.REASONING,
    "market": ModelTier.FAST,
    "news": ModelTier.FAST,
    "risk": ModelTier.REASONING,
    "portfolio": ModelTier.REASONING,
    "synthesis": ModelTier.REASONING,
}


def validate_category_tier_mapping() -> bool:
    """Verify that the explicitly defined architecture matches the current model assignments."""
    return all(
        case.expected_tier == ARCHITECTURE_TIER_MAP[case.category]
        for case in EVALUATION_DATASET
    )


EVALUATION_DATASET: list[EvaluationCase] = [
    EvaluationCase(
        case_id="finance-statement-interpretation",
        category="finance",
        question=(
            "Based on the provided financial statement excerpt for TechCorp (FY2025): "
            "Revenue: $500M, Operating Expenses: $350M, Net Income: $100M, Operating Cash Flow: $120M. "
            "Analyze TechCorp's profitability and cash flow generation using these exact figures."
        ),
        reference_answer=(
            "TechCorp generated $500M in revenue with net income of $100M (20% net margin) "
            "and operating cash flow of $120M, indicating strong profitability and solid cash flow conversion."
        ),
        required_concepts=[
            ["$500m", "$500M", "$500 million", "$500,000,000"],
            ["net income", "net profit"],
            ["cash flow", "operating cash flow", "ocf"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="finance-numerical-reasoning",
        category="finance",
        question=(
            "Financial evidence for Alpha Inc: Gross Profit = $80 million, Revenue = $200 million, "
            "Total Debt = $50 million, Total Equity = $100 million. "
            "Calculate the gross margin percentage and the debt-to-equity ratio, showing your numerical reasoning."
        ),
        reference_answer=(
            "Alpha Inc has a gross margin of 40% ($80M / $200M) and a debt-to-equity ratio of 0.5 ($50M debt / $100M equity)."
        ),
        required_concepts=[
            ["40%", "40.0%", "40 percent"],
            [
                "0.5 debt-to-equity",
                "0.5 debt to equity",
                "debt-to-equity of 0.5",
                "debt to equity of 0.5",
                "debt-to-equity ratio of 0.5",
                "debt to equity ratio of 0.5",
                "debt-to-equity ratio: 0.5",
                "debt to equity ratio: 0.5",
                "d/e of 0.5",
                "d/e ratio of 0.5",
                "0.5 d/e",
            ],
            ["gross margin", "gross profit margin"],
            ["debt-to-equity", "debt to equity", "d/e"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="finance-missing-data-leverage",
        category="finance",
        question=(
            "Given financial data for Beta Ltd: Revenue = $120 million, EBITDA = $30 million. "
            "Operating Cash Flow and Debt figures are unavailable. "
            "Evaluate Beta Ltd's financial leverage and debt coverage."
        ),
        reference_answer=(
            "Beta Ltd generated $120M revenue and $30M EBITDA. However, Total Debt and Operating Cash Flow "
            "data are missing, so financial leverage and debt coverage cannot be calculated without inventing facts."
        ),
        required_concepts=[
            ["ebitda", "ebitda of $30 million"],
            ["missing", "unavailable", "not provided", "not disclosed", "cannot be determined"],
            ["leverage", "debt coverage"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="finance-evidence-grounded",
        category="finance",
        question=(
            "Evidence provided: Gamma Corp FY2025 revenue grew 15% year-over-year to $460 million, "
            "and Free Cash Flow increased from $40 million to $50 million. No guidance or market share data is provided. "
            "Describe Gamma Corp's revenue and cash flow growth strictly based on this evidence."
        ),
        reference_answer=(
            "Based strictly on supplied evidence, Gamma Corp achieved 15% revenue growth to $460 million "
            "and free cash flow growth from $40 million to $50 million. No market share or forward projections are assumed."
        ),
        required_concepts=[
            ["15%", "15.0%", "15 percent"],
            ["$460 million", "$460M", "$460m", "$460,000,000"],
            ["free cash flow", "fcf"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="finance-overall-conclusion",
        category="finance",
        question=(
            "Financial evidence for Delta Corp: Revenue = $1.2 billion (up 8% YoY), Net Profit Margin = 15%, "
            "Total Debt = $300 million, Cash and Cash Equivalents = $450 million, Operating Cash Flow = $220 million. "
            "Synthesize an overall financial conclusion regarding Delta Corp's liquidity, solvency, and operational performance."
        ),
        reference_answer=(
            "Delta Corp demonstrates strong performance: top-line revenue reached $1.2 billion (8% growth) "
            "with a 15% profit margin. Liquidity and solvency are robust with $450M cash exceeding $300M total debt, "
            "supported by $220M in operating cash flow."
        ),
        required_concepts=[
            ["$1.2 billion", "$1.2B", "$1.2b", "$1,200 million"],
            ["$450 million", "$450M", "$450m", "$450,000,000"],
            ["liquidity", "liquid assets", "net cash"],
            ["solvency", "debt position", "capital structure"],
            ["profit margin", "net profit margin", "15%"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["finance"],
        expected_route="financial",
        expected_agents=["financial", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-price-daily-change",
        category="market",
        question=(
            "Market data provided for Apex Corp (NASDAQ: APEX): Current Price = $185.50, Daily Change = +$4.25 (+2.35%), Previous Close = $181.25. "
            "Analyze APEX's current market price and daily price movement based strictly on this evidence."
        ),
        reference_answer=(
            "Apex Corp (NASDAQ: APEX) is trading at $185.50, reflecting a gain of +$4.25 (+2.35%) over its previous close of $181.25."
        ),
        required_concepts=[
            ["$185.50", "$185.5", "185.50"],
            ["2.35%", "2.35 percent", "+2.35%"],
            ["$4.25", "$4.25 gain", "+$4.25", "gained $4.25"],
            ["$181.25", "previous close of $181.25", "closed at $181.25"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-volume-trading-activity",
        category="market",
        question=(
            "Market trading evidence for Zenith Tech (NYSE: ZNT): Current Daily Trading Volume = 8.5 million shares, 90-Day Average Volume = 4.2 million shares. "
            "Assess ZNT's trading volume activity relative to its baseline."
        ),
        reference_answer=(
            "Zenith Tech (NYSE: ZNT) experienced elevated trading activity with daily volume reaching 8.5 million shares, more than double its 90-day average volume of 4.2 million shares."
        ),
        required_concepts=[
            ["8.5 million", "8.5m", "8.5 million shares"],
            ["4.2 million", "4.2m", "4.2 million shares"],
            ["volume", "trading volume", "trading activity"],
            ["elevated", "higher than average", "above average", "increased volume", "more than double"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-52week-range-positioning",
        category="market",
        question=(
            "Market range data for Nova Dynamics (NASDAQ: NVD): Current Price = $92.00, 52-Week High = $95.00, 52-Week Low = $50.00. "
            "Evaluate NVD's current price position relative to its 52-week trading range."
        ),
        reference_answer=(
            "Nova Dynamics (NASDAQ: NVD) is trading at $92.00, placing it near the top of its 52-week range ($50.00 to $95.00) and just $3.00 below its 52-week high."
        ),
        required_concepts=[
            ["$92.00", "$92", "92.00"],
            ["$95.00", "$95", "52-week high of $95.00", "52-week high of $95"],
            ["$50.00", "$50", "52-week low of $50.00", "52-week low of $50"],
            ["near the high", "near its high", "upper end of the range", "near 52-week high", "top of its range", "near high"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-exchange-comparison",
        category="market",
        question=(
            "Market evidence for two competing cloud software companies: Company Alpha (NASDAQ) Price = $210.00, Market Cap = $120 Billion. "
            "Company Beta (NYSE) Price = $70.00, Market Cap = $140 Billion. Compare the market valuation and share prices of Alpha and Beta."
        ),
        reference_answer=(
            "While Company Alpha (NASDAQ) has a higher share price ($210.00 vs $70.00), Company Beta (NYSE) holds a higher overall market capitalization ($140 Billion vs $120 Billion), "
            "demonstrating that share price alone does not reflect total market value."
        ),
        required_concepts=[
            ["$140 billion", "$140B", "$140b", "140 billion"],
            ["$120 billion", "$120B", "$120b", "120 billion"],
            ["market cap", "market capitalization"],
            ["beta has a higher market cap", "beta's market cap is higher", "beta is larger by market cap", "higher market cap for beta"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="market-missing-data-cautious",
        category="market",
        question=(
            "Market update for Quantum Energy (NYSE: QTE): Current Price = $45.00, Market Cap = $12 Billion. "
            "Daily Trading Volume, Bid/Ask Spread, and 52-Week Range metrics are missing/unavailable. Provide a market assessment for QTE."
        ),
        reference_answer=(
            "Quantum Energy (NYSE: QTE) trades at $45.00 with a $12 Billion market cap. However, because trading volume, bid-ask spread, and 52-week range data are missing, "
            "a complete market liquidity and volatility assessment cannot be provided without inventing facts."
        ),
        required_concepts=[
            ["$45.00", "$45", "45.00"],
            ["$12 billion", "$12B", "$12b", "12 billion"],
            ["missing", "unavailable", "not provided", "not disclosed", "cannot be determined"],
            ["trading volume", "volume", "liquidity"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["market"],
        expected_route="market",
        expected_agents=["market", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-sentiment-classification",
        category="news",
        question=(
            "An earnings article reports that FY2025 revenue grew 22% YoY to $310M, exceeding consensus estimates of $295M. "
            "Assess the news sentiment and key evidence."
        ),
        reference_answer=(
            "The news sentiment is positive (bullish) as FY2025 revenue grew 22% YoY to $310M, exceeding consensus estimates of $295M."
        ),
        required_concepts=[
            ["22%", "22 percent"],
            ["$310 million", "$310M"],
            ["positive", "bullish"],
            ["exceeded", "beat estimates"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-headline-evidence",
        category="news",
        question=(
            "A company press release announces the immediate resignation of CEO Jane Doe and appointment of interim CEO John Smith. "
            "Identify the key leadership event."
        ),
        reference_answer=(
            "The press release announces a key leadership transition: the immediate resignation of CEO Jane Doe and the appointment of interim CEO John Smith."
        ),
        required_concepts=[
            ["jane doe"],
            ["john smith"],
            ["resignation", "resigned"],
            ["ceo", "chief executive"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-event-impact-assessment",
        category="news",
        question=(
            "Biotech news confirms FDA approval for Phase 3 oncology drug Therapy-X, with commercial launch set for Q3. "
            "Assess the key event and likely significance."
        ),
        reference_answer=(
            "The key event is FDA approval for Phase 3 oncology drug Therapy-X, which represents a significant milestone leading to a planned commercial launch in Q3."
        ),
        required_concepts=[
            ["fda", "food and drug administration"],
            ["approval", "approved"],
            ["therapy-x", "oncology drug"],
            ["commercial launch"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-missing-data-handling",
        category="news",
        question=(
            "An unverified social media report alleges acquisition talks worth $2 Billion. "
            "An official company statement and regulatory filings are missing or unavailable. How should this news be interpreted?"
        ),
        reference_answer=(
            "The $2 Billion acquisition rumor is unconfirmed and unverified. Because official company statements and regulatory filings are missing, "
            "it must be interpreted cautiously without confirming unverified claims."
        ),
        required_concepts=[
            ["$2 billion", "$2B"],
            ["unconfirmed", "rumor", "unverified"],
            ["missing", "unavailable", "not disclosed"],
            ["cautious", "cannot confirm"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="news-overall-synthesis",
        category="news",
        question=(
            "A multi-source news set reports Q4 profit margin expansion to 18%, a new product announcement, and a pending antitrust review. "
            "Provide an overall news-impact synthesis."
        ),
        reference_answer=(
            "The overall news impact is mixed: positive operational momentum from Q4 profit margin expansion to 18% and a new product announcement "
            "is tempered by regulatory uncertainty surrounding a pending antitrust review."
        ),
        required_concepts=[
            ["18%", "18 percent"],
            ["margin expansion", "profit margin"],
            ["antitrust", "regulatory review"],
            ["synthesis", "overall news impact"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["news"],
        expected_route="news",
        expected_agents=["news", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-concentration-diversification",
        category="risk",
        question=(
            "Portfolio asset allocation: Tech Sector = 65%, Healthcare = 20%, Energy = 10%, Cash = 5%. "
            "Total portfolio value = $1,000,000. Evaluate the portfolio's concentration risk and diversification level."
        ),
        reference_answer=(
            "The portfolio exhibits high concentration risk with 65% allocated to the Tech Sector, "
            "leaving it vulnerable to sector-specific downturns despite modest diversification across Healthcare and Energy."
        ),
        required_concepts=[
            ["65%", "65 percent", "65.0%"],
            ["concentration", "concentration risk", "highly concentrated"],
            ["diversification", "diversified", "lack of diversification"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-volatility-analysis",
        category="risk",
        question=(
            "Risk metrics provided for Stock A and Benchmark Index: Stock A Annualized Volatility = 28.5%, "
            "Benchmark Annualized Volatility = 14.0%, Beta = 1.6. Analyze Stock A's volatility risk relative to the benchmark market."
        ),
        reference_answer=(
            "Stock A exhibits high volatility risk with an annualized volatility of 28.5% compared to the benchmark's 14.0%, "
            "further reflected in a high Beta of 1.6 indicating amplified market sensitivity."
        ),
        required_concepts=[
            ["28.5%", "28.5 percent"],
            ["14%", "14.0%", "14.0 percent", "14 percent"],
            ["volatility", "annualized volatility"],
            ["beta", "beta of 1.6", "1.6"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-downside-max-drawdown",
        category="risk",
        question=(
            "Historical risk metrics for Strategy X: Maximum Drawdown = -22.4%, Value at Risk (95% VaR) = -3.8% daily, "
            "Downside Deviation = 11.2%. Assess Strategy X's downside risk profile and maximum peak-to-trough loss potential."
        ),
        reference_answer=(
            "Strategy X faces substantial downside risk with a maximum drawdown of -22.4% (peak-to-trough loss) "
            "and a daily 95% Value at Risk (VaR) of -3.8%, indicating significant tail risk during adverse market conditions."
        ),
        required_concepts=[
            ["-22.4%", "22.4%", "22.4 percent"],
            ["downside", "downside risk", "downside deviation"],
            ["max drawdown", "maximum drawdown", "drawdown"],
            ["var", "value at risk"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-adjusted-sharpe-ratio",
        category="risk",
        question=(
            "Investment Fund Y evidence: Annualized Return = 14.0%, Risk-Free Rate = 4.0%, Annualized Volatility = 12.0%, "
            "Sharpe Ratio = 0.83 (Risk-Adjusted Return = [14.0% - 4.0%] / 12.0%). Evaluate Fund Y's risk-adjusted performance using the supplied Sharpe ratio."
        ),
        reference_answer=(
            "Fund Y generated an excess return of 10.0% over 12.0% volatility, producing a Sharpe ratio of 0.83, "
            "demonstrating positive risk-adjusted performance per unit of total risk."
        ),
        required_concepts=[
            ["sharpe", "sharpe ratio"],
            [
                "0.83 sharpe",
                "sharpe ratio of 0.83",
                "sharpe ratio: 0.83",
                "sharpe of 0.83",
                "0.83 sharpe ratio",
                "0.83",
            ],
            ["risk-adjusted", "risk adjusted", "risk-adjusted return"],
            ["14%", "14.0%", "14.0 percent", "14 percent"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="risk-missing-data-conclusion",
        category="risk",
        question=(
            "Risk data for Corporate Debt Portfolio: Average Duration = 4.2 years, High Yield Allocation = 35%. "
            "Credit default probabilities, liquidity buffers, and stress test scenario results are missing/unavailable. "
            "Synthesize a risk conclusion regarding this portfolio."
        ),
        reference_answer=(
            "The portfolio carries elevated credit risk given a 35% High Yield allocation and 4.2-year duration. "
            "However, because credit default probabilities and stress testing results are missing, a conclusive downside risk rating cannot be assigned without inventing unverified facts."
        ),
        required_concepts=[
            ["35%", "35.0%", "35 percent"],
            ["high yield", "credit risk"],
            ["missing", "unavailable", "not provided", "not disclosed", "cannot be determined"],
            ["stress test", "stress testing", "default probabilities"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["risk"],
        expected_route="risk",
        expected_agents=["risk", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-allocation-rebalancing",
        category="portfolio",
        question=(
            "Current portfolio allocation: Equities = 70%, Fixed Income = 20%, Cash = 10%. "
            "Target asset allocation policy: Equities = 50%, Fixed Income = 40%, Cash = 10%. "
            "Total portfolio value = $500,000. Analyze the required rebalancing strategy to realign the portfolio with target weights."
        ),
        reference_answer=(
            "The portfolio requires rebalancing: Equities are currently overweighted at 70% ($350,000) versus the 50% target ($250,000), "
            "requiring a $100,000 trim. Fixed Income is underweighted at 20% ($100,000) versus the 40% target ($200,000), requiring a $100,000 addition."
        ),
        required_concepts=[
            ["reduce equities", "trim equities", "decrease equities", "equities from 70% to 50%", "70% to 50%", "sell equities", "reduce equity"],
            ["increase fixed income", "add fixed income", "fixed income from 20% to 40%", "20% to 40%", "reallocate to fixed income", "buy fixed income"],
            ["$100,000", "$100k", "100,000"],
            ["rebalancing", "rebalance", "realign"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-optimization-fidelity",
        category="portfolio",
        question=(
            "Deterministic Mean-Variance Portfolio Optimizer results: Optimal Asset Weights: Energy = 40%, Financials = 35%, Cash = 25%. "
            "Expected Annualized Return = 12.5%, Annualized Volatility = 8.0%, Sharpe Ratio = 1.15. "
            "Interpret the optimizer's numerical output and risk-return characteristics."
        ),
        reference_answer=(
            "The optimizer constructed a high-efficiency portfolio allocating 40% to Energy, 35% to Financials, and 25% to Cash. "
            "It achieves an expected return of 12.5% against an 8.0% volatility, resulting in a strong risk-adjusted Sharpe ratio of 1.15."
        ),
        required_concepts=[
            ["40% energy", "40% allocated to energy", "energy = 40%", "energy 40%"],
            ["12.5% return", "12.5% expected return", "return = 12.5%", "return of 12.5%", "expected return of 12.5%", "expected return: 12.5%", "expected return = 12.5%"],
            ["8.0% volatility", "8% volatility", "volatility = 8.0%", "volatility of 8.0%", "volatility of 8%"],
            [
                "sharpe ratio of 1.15",
                "sharpe ratio: 1.15",
                "sharpe of 1.15",
                "1.15 sharpe",
                "sharpe ratio = 1.15",
            ],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-risk-return-sharpe",
        category="portfolio",
        question=(
            "Portfolio Option A: Expected Return = 10.0%, Volatility = 6.0%, Sharpe Ratio = 1.00. "
            "Portfolio Option B: Expected Return = 13.0%, Volatility = 12.0%, Sharpe Ratio = 0.75. "
            "Compare Options A and B on a risk-adjusted basis and recommend the optimal portfolio for a risk-conscious investor."
        ),
        reference_answer=(
            "Portfolio Option A delivers superior risk-adjusted performance with a Sharpe ratio of 1.00 compared to Option B's 0.75. "
            "Although Option B offers higher nominal return (13.0% vs 10.0%), Option A generates more excess return per unit of volatility (6.0% vs 12.0%)."
        ),
        required_concepts=[
            [
                "sharpe ratio of 1.00",
                "sharpe ratio of 1.0",
                "sharpe ratio: 1.00",
                "sharpe of 1.00",
                "sharpe of 1.0",
                "1.00 sharpe",
                "1.0 sharpe",
                "option a sharpe ratio",
                "sharpe = 1.00",
                "sharpe = 1.0",
            ],
            [
                "sharpe ratio of 0.75",
                "sharpe ratio: 0.75",
                "sharpe of 0.75",
                "0.75 sharpe",
                "option b sharpe ratio",
                "sharpe = 0.75",
            ],
            ["risk-adjusted", "risk adjusted", "risk-adjusted performance"],
            ["option a", "portfolio option a", "portfolio a"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-constraints-missing-data",
        category="portfolio",
        question=(
            "Portfolio Optimization Mandate: Maximum single-stock allocation constraint = 15%. Proposed Asset Z weight = 25%. "
            "Individual asset volatility figures and covariance matrices are missing/unavailable. "
            "Evaluate candidate Asset Z against the portfolio constraint and state whether an optimal risk-weighted allocation can be computed."
        ),
        reference_answer=(
            "Proposed Asset Z allocation of 25% violates the mandatory 15% single-stock concentration constraint. "
            "Furthermore, because individual volatility figures and covariance metrics are missing, a mathematically rigorous optimal risk weight cannot be computed without inventing facts."
        ),
        required_concepts=[
            ["15%", "15 percent", "15.0%"],
            ["violates", "violation", "exceeds", "constraint violation", "breach", "breaches", "non-compliant"],
            ["missing", "unavailable", "not provided", "not disclosed", "cannot be computed"],
            ["covariance", "volatility", "risk metrics"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="portfolio-overall-synthesis",
        category="portfolio",
        question=(
            "Portfolio Synthesis Evidence: Global Growth Portfolio holds Equities = 80%, Fixed Income = 15%, Commodities = 5%. "
            "Annualized Return = 11.5%, Volatility = 9.2%, Sharpe Ratio = 0.92, Max Drawdown = -12.0%. Target Policy: Equities = 65%, Fixed Income = 25%, Commodities = 10%. "
            "Provide an overall portfolio synthesis and conclusion regarding performance, risk profile, and recommended rebalancing."
        ),
        reference_answer=(
            "The Global Growth Portfolio has delivered strong risk-adjusted performance (Sharpe ratio 0.92, 11.5% return, 9.2% volatility, -12.0% drawdown). "
            "However, it is currently equity-heavy at 80% versus the 65% target policy. Rebalancing by trimming Equities and increasing Fixed Income and Commodities will preserve returns while improving diversification."
        ),
        required_concepts=[
            [
                "sharpe ratio of 0.92",
                "sharpe ratio: 0.92",
                "sharpe of 0.92",
                "0.92 sharpe",
                "sharpe ratio = 0.92",
            ],
            ["reduce equities", "trim equities", "decrease equities", "equity reduction"],
            ["increase fixed income", "add fixed income", "increase bonds", "add bonds"],
            ["increase commodities", "add commodities", "increase commodity", "raise commodities", "reallocate to commodities", "allocation to commodities"],
            ["diversification", "risk-adjusted", "risk control"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["portfolio"],
        expected_route="portfolio",
        expected_agents=["portfolio", "risk", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="synthesis-finance-market-cross-agent",
        category="synthesis",
        question=(
            "Financial analysis reports revenue of $500M and a net margin of 20%. "
            "Market analysis reports a share price of $185.50 and a P/E ratio of 25x. "
            "Synthesize these findings and explain how the valuation evidence relates to the company's profitability."
        ),
        reference_answer=(
            "Synthesizing financial and market evidence: TechCorp generated $500M revenue with a 20% net margin. "
            "The market valuation of $185.50 per share at 25x P/E reflects strong investor confidence in its solid profitability."
        ),
        required_concepts=[
            ["$500 million", "$500M"],
            ["20%", "20 percent"],
            ["$185.50", "185.50"],
            ["25x", "25 x", "P/E"],
            ["profitability", "net margin"],
            ["valuation", "valuation evidence"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["synthesis"],
        expected_route="financial",
        expected_agents=["financial", "market", "synthesis"],
    ),
    EvaluationCase(
        case_id="synthesis-risk-portfolio-rebalancing",
        category="synthesis",
        question=(
            "Risk analysis identifies a 65% allocation to the Technology sector. "
            "Portfolio optimization recommends trimming equities by $100k and adding $100k to fixed income. "
            "Synthesize the risk and portfolio findings and explain the rebalancing rationale."
        ),
        reference_answer=(
            "Synthesizing risk and portfolio findings: a 65% Technology allocation creates high sector concentration risk. "
            "Rebalancing by trimming equities by $100k and allocating $100k to fixed income mitigates concentration while improving overall portfolio stability."
        ),
        required_concepts=[
            ["65%", "65 percent"],
            ["technology", "tech"],
            ["$100k", "$100,000"],
            ["fixed income"],
            ["trim equities", "reduce equities", "reduce equity"],
            ["rebalanc", "reallocate"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["synthesis"],
        expected_route="risk",
        expected_agents=["risk", "portfolio", "portfolio_optimization", "synthesis"],
    ),
    EvaluationCase(
        case_id="synthesis-news-market-sentiment-impact",
        category="synthesis",
        question=(
            "News analysis reports FDA approval of an oncology drug. "
            "Market analysis reports trading volume 120% above its average. "
            "Synthesize the news and market evidence and explain the potential market significance without presenting speculation as fact."
        ),
        reference_answer=(
            "Synthesizing news and market evidence: FDA approval of the oncology drug is a major regulatory milestone that correlates with elevated trading volume 120% above average, "
            "indicating potential market significance and heightened investor interest."
        ),
        required_concepts=[
            ["fda", "food and drug administration"],
            ["approval", "approved"],
            ["120%", "120 percent"],
            ["volume", "trading volume"],
            ["market significance", "market impact"],
            ["potential", "may", "could"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["synthesis"],
        expected_route="news",
        expected_agents=["news", "market", "synthesis"],
    ),
    EvaluationCase(
        case_id="synthesis-missing-data-conflicting-evidence",
        category="synthesis",
        question=(
            "Financial analysis shows solid reported financial performance. "
            "Risk analysis lacks credit default probability data. "
            "News analysis contains an unconfirmed takeover rumor. "
            "Synthesize the available evidence while explicitly identifying the missing and unconfirmed information."
        ),
        reference_answer=(
            "While reported financial performance remains solid, data limitations exist: credit default probability data is missing from risk analysis, "
            "and takeover rumors remain unconfirmed. Therefore, a definitive credit risk assessment cannot be confirmed due to limited evidence."
        ),
        required_concepts=[
            ["solid", "strong", "positive"],
            ["missing", "unavailable", "not available"],
            ["credit default", "default probability"],
            ["unconfirmed", "rumor", "unverified"],
            ["cannot confirm", "cannot be confirmed", "uncertain"],
            ["limited evidence", "insufficient evidence", "data limitation"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["synthesis"],
        expected_route="financial",
        expected_agents=["financial", "risk", "news", "synthesis"],
    ),
    EvaluationCase(
        case_id="synthesis-full-investment-recommendation",
        category="synthesis",
        question=(
            "Financial analysis reports 8% revenue growth and a 15% net margin. "
            "Risk analysis reports a 65% Technology concentration. "
            "Market analysis reports a share price of $185.50. "
            "News analysis reports a positive FDA approval event. "
            "Portfolio optimization recommends reducing the concentrated Technology exposure. "
            "Produce a grounded overall research conclusion using these cross-agent findings."
        ),
        reference_answer=(
            "Overall investment research conclusion: Solid fundamentals (8% revenue growth, 15% net margin) and positive FDA approval news support long-term growth at $185.50 per share. "
            "However, high 65% Technology concentration creates risk, so reducing concentrated Tech exposure per portfolio recommendations provides a balanced overall assessment."
        ),
        required_concepts=[
            ["8%", "8 percent"],
            ["15%", "15 percent"],
            ["65%", "65 percent"],
            ["technology", "tech"],
            ["$185.50", "185.50"],
            ["fda", "food and drug administration"],
            ["approval", "approved"],
            ["reduce", "trim", "decrease"],
            ["concentration", "concentrated"],
            ["overall", "conclusion", "assessment"],
        ],
        expected_tier=ARCHITECTURE_TIER_MAP["synthesis"],
        expected_route="financial",
        expected_agents=["financial", "market", "news", "risk", "portfolio", "synthesis"],
    ),
]
