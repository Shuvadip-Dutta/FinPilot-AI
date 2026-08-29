RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_company_profile",
            "description": (
                "Get basic company information such as name, "
                "exchange, country, sector, industry, and description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": (
                            "The stock ticker symbol, for example "
                            "RELIANCE or AAPL."
                        ),
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN", "US"],
                        "description": (
                            "The market where the company is listed."
                        ),
                    },
                },
                "required": [
                    "ticker",
                    "market",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_data",
            "description": (
                "Get current market quote data for a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol.",
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN", "US"],
                        "description": "Market code.",
                    },
                },
                "required": [
                    "ticker",
                    "market",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": (
                "Get financial statements and financial metrics "
                "for a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol.",
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN"],
                        "description": (
                            "Market code. Currently supports India."
                        ),
                    },
                },
                "required": [
                    "ticker",
                    "market",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_key_metrics",
            "description": (
                "Get important financial and valuation metrics "
                "for a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol.",
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN"],
                        "description": (
                            "Market code. Currently supports India."
                        ),
                    },
                },
                "required": [
                    "ticker",
                    "market",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_data",
            "description": (
                "Get historical daily OHLCV market data "
                "for a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol.",
                    },
                    "to_date": {
                        "type": "string",
                        "format": "date",
                        "description": (
                            "End date in YYYY-MM-DD format."
                        ),
                    },
                    "from_date": {
                        "type": ["string", "null"],
                        "format": "date",
                        "description": (
                            "Optional start date in YYYY-MM-DD format."
                        ),
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN"],
                        "description": (
                            "Market code. Currently supports India."
                        ),
                    },
                },
                "required": [
                    "ticker",
                    "to_date",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": (
                "Get recent news articles related to a company."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol.",
                    },
                    "market": {
                        "type": "string",
                        "enum": ["IN"],
                        "description": (
                            "Market code. Currently supports India."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": (
                            "Maximum number of news articles."
                        ),
                    },
                },
                "required": [
                    "ticker",
                ],
                "additionalProperties": False,
            },
        },
    },
]