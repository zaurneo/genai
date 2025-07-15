import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import pandas as pd

from mcp.server.fastmcp import FastMCP
from tools.mcp_servers.stock_data_server.yahoo_client import YahooFinanceClient

print("Initializing Technical Analysis Server...")

# Initialize FastMCP instance
mcp = FastMCP("technical_analysis")

# Initialize Yahoo Finance client at module level
yf_client = YahooFinanceClient()
    
@mcp.tool(description="Calculate technical indicators")
async def calculate_indicators(
    symbol: str,
    indicators: List[str],
    period: str = "3mo"
) -> Dict[str, Any]:
        """Calculate various technical indicators for a stock."""
        try:
            # Get price data
            data = await yf_client.get_historical(symbol, period)
            
            results = {}
            
            for indicator in indicators:
                if indicator.lower() == "sma":
                    results["sma"] = _calculate_sma(data)
                elif indicator.lower() == "ema":
                    results["ema"] = _calculate_ema(data)
                elif indicator.lower() == "rsi":
                    results["rsi"] = _calculate_rsi(data)
                elif indicator.lower() == "macd":
                    results["macd"] = _calculate_macd(data)
                elif indicator.lower() == "bollinger":
                    results["bollinger"] = _calculate_bollinger(data)
                elif indicator.lower() == "stochastic":
                    results["stochastic"] = _calculate_stochastic(data)
            
            # Add current values and signals
            current_close = float(data['Close'].iloc[-1])
            signals = _generate_signals(results, current_close)
            
            return {
                "symbol": symbol.upper(),
                "period": period,
                "indicators": results,
                "current_price": current_close,
                "signals": signals,
                "metadata": {
                    "source": "technical_analysis",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
    
def _calculate_sma(data: pd.DataFrame, periods: List[int] = [20, 50, 200]) -> Dict[str, Any]:
        """Calculate Simple Moving Averages."""
        sma_data = {}
        
        for period in periods:
            if len(data) >= period:
                sma = data['Close'].rolling(window=period).mean()
                sma_data[f"sma_{period}"] = {
                    "current": float(sma.iloc[-1]),
                    "values": sma.dropna().tolist()[-20:]  # Last 20 values
                }
        
        return sma_data
    
def _calculate_ema(data: pd.DataFrame, periods: List[int] = [12, 26]) -> Dict[str, Any]:
        """Calculate Exponential Moving Averages."""
        ema_data = {}
        
        for period in periods:
            if len(data) >= period:
                ema = data['Close'].ewm(span=period, adjust=False).mean()
                ema_data[f"ema_{period}"] = {
                    "current": float(ema.iloc[-1]),
                    "values": ema.dropna().tolist()[-20:]
                }
        
        return ema_data
    
def _calculate_rsi(data: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        """Calculate Relative Strength Index."""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = float(rsi.iloc[-1])
        
        return {
            "current": current_rsi,
            "values": rsi.dropna().tolist()[-20:],
            "overbought": current_rsi > 70,
            "oversold": current_rsi < 30
        }
    
def _calculate_macd(data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate MACD indicator."""
        ema_12 = data['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = data['Close'].ewm(span=26, adjust=False).mean()
        
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd_line": {
                "current": float(macd_line.iloc[-1]),
                "values": macd_line.dropna().tolist()[-20:]
            },
            "signal_line": {
                "current": float(signal_line.iloc[-1]),
                "values": signal_line.dropna().tolist()[-20:]
            },
            "histogram": {
                "current": float(histogram.iloc[-1]),
                "values": histogram.dropna().tolist()[-20:]
            },
            "bullish_crossover": float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]) and float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2]),
            "bearish_crossover": float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]) and float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2])
        }
    
def _calculate_bollinger(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, Any]:
        """Calculate Bollinger Bands."""
        sma = data['Close'].rolling(window=period).mean()
        std = data['Close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = float(data['Close'].iloc[-1])
        
        return {
            "upper_band": {
                "current": float(upper_band.iloc[-1]),
                "values": upper_band.dropna().tolist()[-20:]
            },
            "middle_band": {
                "current": float(sma.iloc[-1]),
                "values": sma.dropna().tolist()[-20:]
            },
            "lower_band": {
                "current": float(lower_band.iloc[-1]),
                "values": lower_band.dropna().tolist()[-20:]
            },
            "bandwidth": float((upper_band.iloc[-1] - lower_band.iloc[-1]) / sma.iloc[-1]),
            "percent_b": float((current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1]))
        }
    
def _calculate_stochastic(data: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
        """Calculate Stochastic Oscillator."""
        low_min = data['Low'].rolling(window=period).min()
        high_max = data['High'].rolling(window=period).max()
        
        k_percent = 100 * ((data['Close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=3).mean()
        
        return {
            "k_line": {
                "current": float(k_percent.iloc[-1]),
                "values": k_percent.dropna().tolist()[-20:]
            },
            "d_line": {
                "current": float(d_percent.iloc[-1]),
                "values": d_percent.dropna().tolist()[-20:]
            },
            "overbought": float(k_percent.iloc[-1]) > 80,
            "oversold": float(k_percent.iloc[-1]) < 20
        }
    
def _generate_signals(indicators: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Generate trading signals based on indicators."""
        signals = {
            "overall": "neutral",
            "strength": 0,
            "recommendations": []
        }
        
        bullish_count = 0
        bearish_count = 0
        
        # RSI signals
        if "rsi" in indicators:
            if indicators["rsi"]["oversold"]:
                bullish_count += 1
                signals["recommendations"].append("RSI indicates oversold condition (potential buy)")
            elif indicators["rsi"]["overbought"]:
                bearish_count += 1
                signals["recommendations"].append("RSI indicates overbought condition (potential sell)")
        
        # MACD signals
        if "macd" in indicators:
            if indicators["macd"]["bullish_crossover"]:
                bullish_count += 2
                signals["recommendations"].append("MACD bullish crossover detected")
            elif indicators["macd"]["bearish_crossover"]:
                bearish_count += 2
                signals["recommendations"].append("MACD bearish crossover detected")
        
        # Bollinger Band signals
        if "bollinger" in indicators:
            percent_b = indicators["bollinger"]["percent_b"]
            if percent_b < 0.2:
                bullish_count += 1
                signals["recommendations"].append("Price near lower Bollinger Band (potential bounce)")
            elif percent_b > 0.8:
                bearish_count += 1
                signals["recommendations"].append("Price near upper Bollinger Band (potential resistance)")
        
        # Determine overall signal
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            if bullish_count > bearish_count:
                signals["overall"] = "bullish"
                signals["strength"] = bullish_count / total_signals
            elif bearish_count > bullish_count:
                signals["overall"] = "bearish"
                signals["strength"] = bearish_count / total_signals
        
        return signals
    
@mcp.tool(description="Analyze chart patterns and trends")
async def analyze_patterns(
    symbol: str,
    period: str = "6mo"
) -> Dict[str, Any]:
        """Identify chart patterns and analyze trends."""
        try:
            # Get price data
            data = await yf_client.get_historical(symbol, period)
            
            # Calculate support and resistance levels
            support_resistance = _find_support_resistance(data)
            
            # Analyze trend
            trend_analysis = _analyze_trend(data)
            
            # Identify patterns
            patterns = _identify_patterns(data)
            
            return {
                "symbol": symbol.upper(),
                "period": period,
                "support_resistance": support_resistance,
                "trend": trend_analysis,
                "patterns": patterns,
                "metadata": {
                    "source": "technical_analysis",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
    
def _find_support_resistance(data: pd.DataFrame) -> Dict[str, Any]:
        """Find support and resistance levels."""
        # Simple implementation using recent highs and lows
        highs = data['High'].rolling(window=20).max()
        lows = data['Low'].rolling(window=20).min()
        
        # Find unique levels
        resistance_levels = sorted(set(highs.dropna().round(2).tolist()))[-5:]
        support_levels = sorted(set(lows.dropna().round(2).tolist()))[:5]
        
        current_price = float(data['Close'].iloc[-1])
        
        return {
            "resistance_levels": resistance_levels,
            "support_levels": support_levels,
            "nearest_resistance": min([r for r in resistance_levels if r > current_price], default=None),
            "nearest_support": max([s for s in support_levels if s < current_price], default=None)
        }
    
def _analyze_trend(data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price trend."""
        closes = data['Close']
        
        # Calculate trend using linear regression
        x = np.arange(len(closes))
        y = closes.values
        
        # Fit linear regression
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # Calculate trend strength
        sma_20 = closes.rolling(window=20).mean()
        sma_50 = closes.rolling(window=50).mean()
        
        trend_direction = "uptrend" if slope > 0 else "downtrend"
        trend_strength = abs(slope) / closes.mean() * 100  # Percentage slope
        
        return {
            "direction": trend_direction,
            "strength": float(trend_strength),
            "slope": float(slope),
            "sma_alignment": "bullish" if float(sma_20.iloc[-1]) > float(sma_50.iloc[-1]) else "bearish"
        }
    
def _identify_patterns(data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify common chart patterns."""
        patterns = []
        
        # Simple pattern detection (would be more sophisticated in production)
        closes = data['Close'].values
        
        # Double bottom pattern
        if len(closes) >= 30:
            recent = closes[-30:]
            min_idx = np.argmin(recent)
            
            if 5 < min_idx < 25:  # Minimum not at edges
                left_valley = recent[:min_idx]
                right_valley = recent[min_idx:]
                
                if len(left_valley) > 5 and len(right_valley) > 5:
                    left_min = np.min(left_valley)
                    right_min = np.min(right_valley)
                    
                    if abs(left_min - recent[min_idx]) / recent[min_idx] < 0.02:
                        patterns.append({
                            "pattern": "double_bottom",
                            "confidence": 0.7,
                            "description": "Potential double bottom pattern detected"
                        })
        
        return patterns
    
@mcp.tool(description="Compare performance between multiple stocks")
async def compare_performance(
    symbols: List[str],
    period: str = "1y",
    metrics: List[str] = ["returns", "volatility", "sharpe"]
) -> Dict[str, Any]:
        """Compare performance metrics between multiple stocks."""
        try:
            comparison_data = {}
            
            for symbol in symbols:
                data = await yf_client.get_historical(symbol, period)
                
                # Calculate returns
                returns = data['Close'].pct_change().dropna()
                
                # Calculate metrics
                symbol_metrics = {}
                
                if "returns" in metrics:
                    total_return = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100
                    symbol_metrics["total_return"] = float(total_return)
                    symbol_metrics["annualized_return"] = float(total_return * (252 / len(data)))
                
                if "volatility" in metrics:
                    symbol_metrics["volatility"] = float(returns.std() * np.sqrt(252) * 100)
                
                if "sharpe" in metrics:
                    # Assuming risk-free rate of 2%
                    risk_free_rate = 0.02
                    excess_returns = returns.mean() * 252 - risk_free_rate
                    sharpe_ratio = excess_returns / (returns.std() * np.sqrt(252))
                    symbol_metrics["sharpe_ratio"] = float(sharpe_ratio)
                
                # Add correlation data
                comparison_data[symbol] = {
                    "metrics": symbol_metrics,
                    "price_data": {
                        "current": float(data['Close'].iloc[-1]),
                        "start": float(data['Close'].iloc[0]),
                        "high": float(data['High'].max()),
                        "low": float(data['Low'].min())
                    }
                }
            
            # Calculate correlations
            if len(symbols) > 1:
                correlation_matrix = await _calculate_correlations(symbols, period)
                comparison_data["correlations"] = correlation_matrix
            
            return {
                "symbols": symbols,
                "period": period,
                "comparison": comparison_data,
                "metadata": {
                    "source": "technical_analysis",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "symbols": symbols,
                "timestamp": datetime.now().isoformat()
            }
    
async def _calculate_correlations(symbols: List[str], period: str) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between stocks."""
        price_data = {}
        
        for symbol in symbols:
            data = await yf_client.get_historical(symbol, period)
            price_data[symbol] = data['Close']
        
        # Create DataFrame and calculate correlations
        df = pd.DataFrame(price_data)
        correlation_matrix = df.corr()
        
        # Convert to nested dict
        result = {}
        for symbol1 in symbols:
            result[symbol1] = {}
            for symbol2 in symbols:
                result[symbol1][symbol2] = float(correlation_matrix.loc[symbol1, symbol2])
        
        return result

if __name__ == "__main__":
    # Run with default stdio transport for now
    mcp.run()