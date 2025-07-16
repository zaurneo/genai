"""Formatters for stock data server responses."""
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.mcp_servers.shared import (
    BaseFormatter,
    format_currency,
    format_number,
    format_percentage,
    format_change,
    format_large_number,
    format_date,
    format_time_period,
    create_table
)


class StockDataFormatter(BaseFormatter):
    """Formatter for stock market data responses."""
    
    def format_response(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format stock data response based on the type of data."""
        # Route to appropriate formatter based on data structure
        if "data" in data and isinstance(data.get("data"), list):
            return self._format_price_data(data, context)
        elif "company_info" in data:
            return self._format_fundamentals(data, context)
        elif "financial_data" in data:
            return self._format_financials(data, context)
        else:
            return self.format_empty_response(context)
    
    def format_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error messages for stock data requests."""
        symbol = context.get("symbol", "the requested stock") if context else "the requested stock"
        
        error_lower = error.lower()
        if "rate limit" in error_lower or "429" in error:
            return f"Market data is temporarily unavailable due to rate limiting. Please try again in a few moments."
        elif "not found" in error_lower or "404" in error:
            return f"Unable to find data for {symbol}. Please verify the ticker symbol."
        elif "timeout" in error_lower:
            return f"Request timed out while fetching data for {symbol}. Please try again."
        elif "connection" in error_lower:
            return f"Unable to connect to market data provider. Please check your connection and try again."
        else:
            return f"An error occurred while fetching data for {symbol}: {error}"
    
    def _format_price_data(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format price data response."""
        symbol = data.get("symbol", "Unknown")
        period = format_time_period(data.get("period", "1d"))
        price_data = data.get("data", [])
        stats = data.get("statistics", {})
        
        if not price_data:
            return f"No price data available for {symbol}. The market data might be temporarily unavailable."
        
        # Get latest price info
        latest = price_data[-1]
        latest_date = latest.get("date", latest.get("Date", "Unknown date"))
        close_price = latest.get("close", latest.get("Close", 0))
        volume = latest.get("volume", latest.get("Volume", 0))
        
        # Format basic info
        lines = [
            f"Stock Price Data for {symbol}",
            f"Period: {period}",
            f"Latest Date: {latest_date}",
            "",
            f"Current Price: {format_currency(close_price)}",
            f"Volume: {format_large_number(volume)}",
        ]
        
        # Add statistics if available
        if stats:
            lines.extend([
                "",
                "Statistics:",
                f"  High: {format_currency(stats.get('high', 0))}",
                f"  Low: {format_currency(stats.get('low', 0))}",
                f"  Average: {format_currency(stats.get('avg_close', 0))}",
                f"  Volatility: {format_percentage(stats.get('volatility', 0) * 100)}"
            ])
        
        # Add price change if we have previous data
        if len(price_data) > 1:
            prev_close = price_data[-2].get("close", price_data[-2].get("Close", close_price))
            change = format_change(close_price, prev_close)
            lines.insert(5, f"Change: {change}")
        
        return "\n".join(lines)
    
    def _format_fundamentals(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format fundamental data response."""
        symbol = data.get("symbol", "Unknown")
        info = data.get("company_info", {})
        metrics = data.get("key_metrics", {})
        
        if not info and not metrics:
            return f"No fundamental data available for {symbol}."
        
        lines = [f"Fundamental Analysis for {symbol}"]
        
        # Company info
        if info:
            lines.extend([
                "",
                "Company Information:",
                f"  Name: {info.get('longName', 'N/A')}",
                f"  Sector: {info.get('sector', 'N/A')}",
                f"  Industry: {info.get('industry', 'N/A')}",
                f"  Market Cap: {format_large_number(info.get('marketCap', 0))}",
                f"  Employees: {format_number(info.get('fullTimeEmployees', 0), 0)}"
            ])
        
        # Key metrics
        if metrics:
            lines.extend([
                "",
                "Key Metrics:",
                f"  P/E Ratio: {format_number(metrics.get('pe_ratio', 0))}",
                f"  P/B Ratio: {format_number(metrics.get('pb_ratio', 0))}",
                f"  Dividend Yield: {format_percentage(metrics.get('dividend_yield', 0) * 100)}",
                f"  52-Week High: {format_currency(metrics.get('52_week_high', 0))}",
                f"  52-Week Low: {format_currency(metrics.get('52_week_low', 0))}"
            ])
        
        return "\n".join(lines)
    
    def _format_financials(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format financial statements data."""
        symbol = data.get("symbol", "Unknown")
        statement_type = data.get("statement_type", "financial")
        financial_data = data.get("financial_data", {})
        
        if not financial_data:
            return f"No financial data available for {symbol}."
        
        lines = [f"{statement_type.title()} Statement for {symbol}"]
        
        # Income statement
        income = financial_data.get("income_statement", {})
        if income:
            lines.extend([
                "",
                "Income Statement (Latest):",
                f"  Date: {income.get('date', 'N/A')}"
            ])
            
            # Map common field names
            if 'totalRevenue' in income:
                lines.append(f"  Revenue: {format_currency(income['totalRevenue'])}")
            if 'netIncome' in income:
                lines.append(f"  Net Income: {format_currency(income['netIncome'])}")
            if 'grossProfit' in income:
                lines.append(f"  Gross Profit: {format_currency(income['grossProfit'])}")
            if 'operatingIncome' in income:
                lines.append(f"  Operating Income: {format_currency(income['operatingIncome'])}")
        
        # Balance sheet
        balance = financial_data.get("balance_sheet", {})
        if balance:
            lines.extend([
                "",
                "Balance Sheet (Latest):",
                f"  Date: {balance.get('date', 'N/A')}"
            ])
            
            if 'totalAssets' in balance:
                lines.append(f"  Total Assets: {format_currency(balance['totalAssets'])}")
            if 'totalLiabilities' in balance:
                lines.append(f"  Total Liabilities: {format_currency(balance['totalLiabilities'])}")
            if 'totalStockholderEquity' in balance:
                lines.append(f"  Shareholder Equity: {format_currency(balance['totalStockholderEquity'])}")
            if 'cash' in balance:
                lines.append(f"  Cash: {format_currency(balance['cash'])}")
        
        # Cash flow
        cashflow = financial_data.get("cash_flow", {})
        if cashflow:
            lines.extend([
                "",
                "Cash Flow (Latest):",
                f"  Date: {cashflow.get('date', 'N/A')}"
            ])
            
            if 'operatingCashflow' in cashflow:
                lines.append(f"  Operating Cash Flow: {format_currency(cashflow['operatingCashflow'])}")
            if 'freeCashFlow' in cashflow:
                lines.append(f"  Free Cash Flow: {format_currency(cashflow['freeCashFlow'])}")
        
        return "\n".join(lines)


# Create a singleton instance for use in the server
formatter = StockDataFormatter()