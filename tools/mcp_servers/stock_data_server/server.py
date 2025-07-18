import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from mcp.server.fastmcp import FastMCP
from tools.mcp_servers.stock_data_server.yahoo_client import YahooFinanceClient
from tools.mcp_servers.stock_data_server.formatters import formatter

print("Initializing Stock Data Server...")

# Initialize FastMCP instance
mcp = FastMCP("stock_data")

# Initialize Yahoo Finance client at module level
yf_client = YahooFinanceClient()
    
@mcp.tool(description="Fetch stock price and volume data")
async def get_price(
    symbol: str, 
    period: str = "1mo",
    interval: str = "1d"
) -> Dict[str, Any]:
        """Get historical price data for a stock."""
        try:
            data = await yf_client.get_historical(symbol, period, interval)
            
            # Convert to serializable format
            price_data = []
            for index, row in data.iterrows():
                price_data.append({
                    "date": index.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "adjusted_close": float(row.get("Adj Close", row["Close"]))
                })
            
            # Calculate basic statistics
            latest = price_data[-1] if price_data else None
            first = price_data[0] if price_data else None
            
            stats = {}
            if latest and first:
                change = latest["close"] - first["close"]
                change_pct = (change / first["close"]) * 100
                
                stats = {
                    "current_price": latest["close"],
                    "period_change": change,
                    "period_change_pct": change_pct,
                    "period_high": max(p["high"] for p in price_data),
                    "period_low": min(p["low"] for p in price_data),
                    "avg_volume": sum(p["volume"] for p in price_data) / len(price_data)
                }
            
            # Create response data
            response_data = {
                "symbol": symbol.upper(),
                "period": period,
                "interval": interval,
                "data": price_data,
                "statistics": stats,
                "metadata": {
                    "source": "yahoo_finance",
                    "timestamp": datetime.now().isoformat(),
                    "data_points": len(price_data)
                }
            }
            
            # Format human-readable response
            context = {"symbol": symbol, "period": period}
            formatted_response = formatter.format_response(response_data, context)
            response_data["formatted"] = formatted_response
            
            return response_data
        except Exception as e:
            context = {"symbol": symbol, "period": period}
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "formatted": formatter.format_error(str(e), context)
            }
    
@mcp.tool(description="Get company fundamentals")
async def get_fundamentals(symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a company."""
        try:
            info = await yf_client.get_info(symbol)
            
            # Extract key fundamentals
            fundamentals = {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "earnings_per_share": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "return_on_equity": info.get("returnOnEquity"),
                "return_on_assets": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "average_volume": info.get("averageVolume"),
                "shares_outstanding": info.get("sharesOutstanding")
            }
            
            # Company information
            company_info = {
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary"),
                "employees": info.get("fullTimeEmployees")
            }
            
            # Create response data
            response_data = {
                "symbol": symbol.upper(),
                "fundamentals": fundamentals,
                "company": company_info,
                "company_info": company_info,  # Add for formatter compatibility
                "key_metrics": fundamentals,    # Add for formatter compatibility
                "metadata": {
                    "source": "yahoo_finance",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Format human-readable response
            context = {"symbol": symbol}
            formatted_response = formatter.format_response(response_data, context)
            response_data["formatted"] = formatted_response
            
            return response_data
        except Exception as e:
            context = {"symbol": symbol}
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "formatted": formatter.format_error(str(e), context)
            }
    
@mcp.tool(description="Get financial statements")
async def get_financials(
    symbol: str,
    statement_type: str = "income"
) -> Dict[str, Any]:
        """Get financial statements for a company."""
        try:
            if statement_type == "income":
                data = await yf_client.get_income_statement(symbol)
            elif statement_type == "balance":
                data = await yf_client.get_balance_sheet(symbol)
            elif statement_type == "cashflow":
                data = await yf_client.get_cashflow(symbol)
            else:
                raise ValueError(f"Invalid statement type: {statement_type}")
            
            # Convert to serializable format
            statements = []
            for date, values in data.items():
                statement = {"date": date.isoformat()}
                for key, value in values.items():
                    statement[key] = float(value) if value is not None else None
                statements.append(statement)
            
            # Create response data structure matching formatter expectations
            financial_data = {}
            if statement_type == "income":
                financial_data["income_statement"] = statements[0] if statements else {}
            elif statement_type == "balance":
                financial_data["balance_sheet"] = statements[0] if statements else {}
            elif statement_type == "cashflow":
                financial_data["cash_flow"] = statements[0] if statements else {}
            
            response_data = {
                "symbol": symbol.upper(),
                "statement_type": statement_type,
                "data": statements,
                "financial_data": financial_data,  # Add for formatter compatibility
                "metadata": {
                    "source": "yahoo_finance",
                    "timestamp": datetime.now().isoformat(),
                    "periods": len(statements)
                }
            }
            
            # Format human-readable response
            context = {"symbol": symbol, "statement_type": statement_type}
            formatted_response = formatter.format_response(response_data, context)
            response_data["formatted"] = formatted_response
            
            return response_data
        except Exception as e:
            context = {"symbol": symbol, "statement_type": statement_type}
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "formatted": formatter.format_error(str(e), context)
            }

if __name__ == "__main__":
    # Run with default stdio transport for now
    mcp.run()