import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
import asyncio
from functools import partial

class YahooFinanceClient:
    """Client for fetching data from Yahoo Finance."""
    
    def __init__(self):
        self.cache = {}
    
    async def get_historical(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical price data."""
        loop = asyncio.get_event_loop()
        
        # Run yfinance in executor since it's synchronous
        ticker = yf.Ticker(symbol)
        data = await loop.run_in_executor(
            None,
            partial(ticker.history, period=period, interval=interval)
        )
        
        return data
    
    async def get_info(self, symbol: str) -> Dict[str, Any]:
        """Get company information and fundamentals."""
        loop = asyncio.get_event_loop()
        
        ticker = yf.Ticker(symbol)
        info = await loop.run_in_executor(None, lambda: ticker.info)
        
        return info
    
    async def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """Get income statement data."""
        loop = asyncio.get_event_loop()
        
        ticker = yf.Ticker(symbol)
        data = await loop.run_in_executor(
            None,
            lambda: ticker.financials
        )
        
        return data
    
    async def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Get balance sheet data."""
        loop = asyncio.get_event_loop()
        
        ticker = yf.Ticker(symbol)
        data = await loop.run_in_executor(
            None,
            lambda: ticker.balance_sheet
        )
        
        return data
    
    async def get_cashflow(self, symbol: str) -> pd.DataFrame:
        """Get cash flow statement data."""
        loop = asyncio.get_event_loop()
        
        ticker = yf.Ticker(symbol)
        data = await loop.run_in_executor(
            None,
            lambda: ticker.cashflow
        )
        
        return data