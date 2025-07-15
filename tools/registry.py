"""
Enhanced Tool Registry for Agent-Based Tool Selection

This registry provides detailed metadata about each tool to help the agent
make intelligent decisions about which tools to use based on user queries.
"""

TOOL_REGISTRY = {
    "stock_analyzer": {
        "id": "stock_data.get_price",
        "description": "Analyzes stock prices, historical data, and volume trends",
        "when_to_use": "User asks about stock prices, price history, volume, or wants to see price charts",
        "examples": [
            "What's Apple's stock price?",
            "Show me TSLA price for last month",
            "How has MSFT performed this year?",
            "What's the trading volume for GOOGL?"
        ],
        "requires": ["ticker_symbol"],
        "optional_params": ["time_period", "interval"],
        "output_format": "price data, charts, volume metrics",
        "category": "market_data"
    },
    
    "fundamental_analyzer": {
        "id": "stock_data.get_fundamentals",
        "description": "Provides company fundamentals like PE ratio, market cap, earnings, and key metrics",
        "when_to_use": "User asks about company valuation, earnings, fundamentals, or financial health",
        "examples": [
            "What's Apple's PE ratio?",
            "Show me Tesla's earnings",
            "Is Microsoft overvalued?",
            "What's Amazon's market cap?"
        ],
        "requires": ["ticker_symbol"],
        "output_format": "fundamental metrics, ratios, company overview",
        "category": "fundamental_data"
    },
    
    "financial_statements": {
        "id": "stock_data.get_financials",
        "description": "Retrieves detailed financial statements including income, balance sheet, and cash flow",
        "when_to_use": "User asks for detailed financials, revenue, expenses, assets, or cash flow",
        "examples": [
            "Show me Apple's income statement",
            "What's Tesla's revenue growth?",
            "How much debt does Microsoft have?",
            "What's Amazon's cash flow?"
        ],
        "requires": ["ticker_symbol"],
        "optional_params": ["statement_type"],
        "output_format": "detailed financial statements",
        "category": "fundamental_data"
    },
    
    "technical_indicators": {
        "id": "technical.calculate_indicators",
        "description": "Calculates technical indicators like moving averages, RSI, MACD, and more",
        "when_to_use": "User asks about technical analysis, indicators, or trading signals",
        "examples": [
            "Calculate RSI for AAPL",
            "What's the 50-day moving average for TSLA?",
            "Show me MACD for Microsoft",
            "Is Google oversold?"
        ],
        "requires": ["ticker_symbol", "indicators"],
        "optional_params": ["time_period"],
        "output_format": "technical indicator values and analysis",
        "category": "technical_analysis"
    },
    
    "pattern_analyzer": {
        "id": "technical.analyze_patterns",
        "description": "Identifies chart patterns, support/resistance levels, and trend analysis",
        "when_to_use": "User asks about chart patterns, trends, support levels, or technical setups",
        "examples": [
            "What patterns do you see in AAPL chart?",
            "Where is support for Tesla?",
            "Is Microsoft in an uptrend?",
            "Any breakout patterns in GOOGL?"
        ],
        "requires": ["ticker_symbol"],
        "optional_params": ["time_period"],
        "output_format": "pattern identification, trend analysis, key levels",
        "category": "technical_analysis"
    },
    
    "stock_comparer": {
        "id": "technical.compare_performance",
        "description": "Compares performance metrics between multiple stocks",
        "when_to_use": "User wants to compare stocks, see relative performance, or analyze correlations",
        "examples": [
            "Compare Apple vs Microsoft",
            "Which performed better: TSLA or RIVN?",
            "Show correlation between tech stocks",
            "Compare FAANG stocks performance"
        ],
        "requires": ["ticker_symbols_list"],
        "optional_params": ["time_period", "metrics"],
        "output_format": "comparative analysis, performance charts, correlation data",
        "category": "comparison"
    }
}

# Category descriptions for agent understanding
TOOL_CATEGORIES = {
    "market_data": {
        "description": "Real-time and historical price data, volume, and market activity",
        "use_for": ["price checks", "volume analysis", "price history", "market hours data"]
    },
    "fundamental_data": {
        "description": "Company financials, earnings, valuations, and business metrics",
        "use_for": ["company analysis", "valuation", "financial health", "earnings reports"]
    },
    "technical_analysis": {
        "description": "Technical indicators, chart patterns, and trading signals",
        "use_for": ["trading analysis", "chart patterns", "technical setups", "indicators"]
    },
    "comparison": {
        "description": "Multi-stock comparison and relative performance analysis",
        "use_for": ["comparing stocks", "sector analysis", "relative performance", "correlation"]
    }
}

# Context-aware tool selection hints
CONTEXT_HINTS = {
    "ambiguous_queries": {
        "what about it": "Check context for last analyzed entity and tool used",
        "how about last year": "Apply time period to previous query",
        "and the other one": "Reference to previously mentioned comparison ticker",
        "why did it change": "Likely needs news or event analysis (future tool)",
        "is it good": "Needs context - price performance, fundamentals, or technical setup?"
    },
    
    "implicit_tools": {
        "overvalued/undervalued": ["fundamental_analyzer", "stock_comparer"],
        "buy/sell signal": ["technical_indicators", "pattern_analyzer"],
        "earnings": ["fundamental_analyzer", "financial_statements"],
        "breakout": ["pattern_analyzer", "technical_indicators"]
    }
}

def get_tool_descriptions_for_prompt():
    """
    Generate a formatted string of tool descriptions for the agent's system prompt.
    """
    descriptions = []
    for tool_key, tool_info in TOOL_REGISTRY.items():
        desc = f"""
Tool: {tool_key}
Tool ID: {tool_info['id']}
Description: {tool_info['description']}
When to use: {tool_info['when_to_use']}
Examples: {', '.join(tool_info['examples'][:2])}
Requires: {', '.join(tool_info['requires'])}
"""
        descriptions.append(desc.strip())
    
    return "\n\n".join(descriptions)

def get_tools_by_category(category: str):
    """
    Get all tools in a specific category.
    """
    return {
        key: tool for key, tool in TOOL_REGISTRY.items() 
        if tool.get('category') == category
    }

def match_tool_by_examples(query: str):
    """
    Find tools whose examples match the query pattern.
    This is a helper for the agent, not a replacement for agent decision-making.
    """
    query_lower = query.lower()
    matching_tools = []
    
    for tool_key, tool_info in TOOL_REGISTRY.items():
        for example in tool_info.get('examples', []):
            if any(word in example.lower() for word in query_lower.split()):
                matching_tools.append((tool_key, tool_info))
                break
    
    return matching_tools