from django.test import SimpleTestCase

from apps.ai.graph.router import WorkflowRouter


class WorkflowRouterTestCase(SimpleTestCase):

    def setUp(self):
        self.router = WorkflowRouter()

    def test_financial_query_routes_to_financial(self):
        route = self.router.route(
            "Show Reliance's quarterly revenue and profit."
        )

        self.assertEqual(route, "financial")

    def test_market_price_query_routes_to_market(self):
        route = self.router.route(
            "What is the current share price of TCS?"
        )

        self.assertEqual(route, "market")

    def test_news_query_routes_to_news(self):
        route = self.router.route(
            "Show me the latest news about Infosys."
        )

        self.assertEqual(route, "news")

    def test_unrelated_query_routes_to_general(self):
        route = self.router.route(
            "How can I create a monthly budget?"
        )

        self.assertEqual(route, "general")

    def test_matching_is_case_insensitive(self):
        route = self.router.route(
            "WHAT ARE THE LATEST HEADLINES FOR HDFC?"
        )

        self.assertEqual(route, "news")

    def test_routing_is_deterministic(self):
        message = "What is the current price of Reliance?"

        routes = [
            self.router.route(message)
            for _ in range(3)
        ]

        self.assertEqual(routes, ["market", "market", "market"])
        
    def test_risk_query_routes_to_risk(self):
        self.assertEqual(
            self.router.route(
                "Assess the downside risk of this investment."
            ),
            "risk",
        )

    def test_portfolio_query_routes_to_portfolio(self):
        self.assertEqual(
            self.router.route(
                "Analyze my portfolio allocation."
            ),
            "portfolio",
        )

    def test_comprehensive_multi_domain_query_routes_to_general(self):
        route = self.router.route(
            "Conduct a complete fundamental and market research analysis of Larsen & Toubro (L&T). "
            "Cover company profile, current market data, financial health, recent news, sentiment, key risks."
        )
        self.assertEqual(route, "general")

    def test_news_only_query_routes_to_news(self):
        route = self.router.route(
            "Show me recent news and latest updates for Reliance."
        )
        self.assertEqual(route, "news")

    def test_financial_only_query_routes_to_financial(self):
        route = self.router.route(
            "Show quarterly revenue and earnings statement for Infosys."
        )
        self.assertEqual(route, "financial")

    def test_market_only_query_routes_to_market(self):
        route = self.router.route(
            "What is the share price quote for TCS?"
        )
        self.assertEqual(route, "market")

    def test_production_failed_nvda_valuation_query_routes_to_financial(self):
        route = self.router.route(
            "Assess the current valuation of NVDA (US) based on trailing and forward P/E, EV/EBITDA, and price-to-book ratios. Is it trading at a discount or premium to historical averages?"
        )
        self.assertEqual(route, "financial")

    def test_pe_valuation_query_routes_to_financial(self):
        self.assertEqual(
            self.router.route("What is NVDA's P/E valuation?"),
            "financial",
        )

    def test_ev_ebitda_and_pb_valuation_query_routes_to_financial(self):
        self.assertEqual(
            self.router.route("Compare NVDA EV/EBITDA and P/B"),
            "financial",
        )

    def test_discount_to_historical_valuation_routes_to_financial(self):
        self.assertEqual(
            self.router.route("Is NVDA trading at a discount to its historical valuation?"),
            "financial",
        )

    def test_numeric_trading_at_price_routes_to_market(self):
        self.assertEqual(
            self.router.route("Is NVDA trading at $180?"),
            "market",
        )

    def test_current_stock_price_routes_to_market(self):
        self.assertEqual(
            self.router.route("Show me the current stock price of NVDA"),
            "market",
        )

    def test_valuation_and_recent_news_routes_to_general(self):
        self.assertEqual(
            self.router.route("Assess NVDA valuation and recent news"),
            "general",
        )

    def test_valuation_and_risk_routes_to_general(self):
        self.assertEqual(
            self.router.route("Assess NVDA valuation and risk"),
            "general",
        )
