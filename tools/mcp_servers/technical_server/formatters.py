"""Formatters for technical analysis server responses."""
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


class TechnicalAnalysisFormatter(BaseFormatter):
    """Formatter for technical analysis data responses."""
    
    def format_response(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format technical analysis response based on the type of data."""
        # Route to appropriate formatter based on data structure
        if "indicators" in data:
            return self._format_technical_indicators(data, context)
        elif "patterns" in data and "support_resistance" in data:
            return self._format_chart_analysis(data, context)
        elif "comparison" in data:
            return self._format_performance_comparison(data, context)
        elif "pattern" in data:
            return self._format_pattern_analysis(data, context)
        else:
            return self.format_empty_response(context)
    
    def format_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error messages for technical analysis requests."""
        symbol = context.get("symbol", "the requested stock") if context else "the requested stock"
        
        error_lower = error.lower()
        if "not enough data" in error_lower:
            return f"Insufficient historical data available for {symbol} to calculate the requested indicators."
        elif "invalid indicator" in error_lower:
            return f"Invalid technical indicator requested. Please check the indicator name."
        elif "out-of-bounds" in error_lower or "out of bounds" in error_lower:
            return f"Unable to calculate indicators for {symbol}. The data may be incomplete or unavailable."
        else:
            return f"An error occurred while calculating technical indicators for {symbol}: {error}"
    
    def _format_technical_indicators(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format technical indicators response."""
        symbol = data.get("symbol", "Unknown")
        indicators = data.get("indicators", {})
        signals = data.get("signals", {})
        current_price = data.get("current_price", 0)
        
        if not indicators:
            return f"No technical indicators available for {symbol}."
        
        lines = [
            f"Technical Analysis for {symbol}",
            f"Current Price: {format_currency(current_price)}",
            ""
        ]
        
        # SMA (Simple Moving Average)
        if "sma" in indicators:
            sma_data = indicators["sma"]
            lines.extend([
                "Simple Moving Averages (SMA):",
                f"  20-day: {format_currency(sma_data.get('sma_20', 0))}",
                f"  50-day: {format_currency(sma_data.get('sma_50', 0))}",
                f"  200-day: {format_currency(sma_data.get('sma_200', 0))}"
            ])
        
        # EMA (Exponential Moving Average)
        if "ema" in indicators:
            ema_data = indicators["ema"]
            lines.extend([
                "",
                "Exponential Moving Averages (EMA):",
                f"  12-day: {format_currency(ema_data.get('ema_12', 0))}",
                f"  26-day: {format_currency(ema_data.get('ema_26', 0))}"
            ])
        
        # RSI (Relative Strength Index)
        if "rsi" in indicators:
            rsi_data = indicators["rsi"]
            rsi_value = rsi_data.get("value", 0)
            rsi_signal = self._get_rsi_signal(rsi_value)
            lines.extend([
                "",
                "Relative Strength Index (RSI):",
                f"  Value: {format_number(rsi_value)} {rsi_signal}"
            ])
        
        # MACD (Moving Average Convergence Divergence)
        if "macd" in indicators:
            macd_data = indicators["macd"]
            lines.extend([
                "",
                "MACD:",
                f"  MACD Line: {format_number(macd_data.get('macd', 0), 4)}",
                f"  Signal Line: {format_number(macd_data.get('signal', 0), 4)}",
                f"  Histogram: {format_number(macd_data.get('histogram', 0), 4)}"
            ])
            if macd_data.get('histogram', 0) > 0:
                lines.append("  Signal: Bullish momentum")
            else:
                lines.append("  Signal: Bearish momentum")
        
        # Bollinger Bands
        if "bollinger" in indicators:
            bb_data = indicators["bollinger"]
            lines.extend([
                "",
                "Bollinger Bands:",
                f"  Upper Band: {format_currency(bb_data.get('upper', 0))}",
                f"  Middle Band: {format_currency(bb_data.get('middle', 0))}",
                f"  Lower Band: {format_currency(bb_data.get('lower', 0))}"
            ])
        
        # Stochastic Oscillator
        if "stochastic" in indicators:
            stoch_data = indicators["stochastic"]
            k_value = stoch_data.get('k', 0)
            d_value = stoch_data.get('d', 0)
            lines.extend([
                "",
                "Stochastic Oscillator:",
                f"  %K: {format_number(k_value)}",
                f"  %D: {format_number(d_value)}"
            ])
            if k_value > 80:
                lines.append("  Signal: Overbought")
            elif k_value < 20:
                lines.append("  Signal: Oversold")
        
        # Overall signals
        if signals:
            lines.extend([
                "",
                "Trading Signals:",
                f"  Trend: {signals.get('trend', 'Neutral')}",
                f"  Momentum: {signals.get('momentum', 'Neutral')}",
                f"  Recommendation: {signals.get('recommendation', 'Hold')}"
            ])
        
        return "\n".join(lines)
    
    def _format_pattern_analysis(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format pattern analysis response."""
        symbol = data.get("symbol", "Unknown")
        patterns = data.get("patterns", [])
        
        if not patterns:
            return f"No chart patterns detected for {symbol}."
        
        lines = [f"Chart Pattern Analysis for {symbol}", ""]
        
        for pattern in patterns:
            lines.extend([
                f"Pattern: {pattern.get('name', 'Unknown')}",
                f"  Type: {pattern.get('type', 'Unknown')}",
                f"  Confidence: {format_percentage(pattern.get('confidence', 0) * 100)}",
                f"  Target Price: {format_currency(pattern.get('target_price', 0))}",
                ""
            ])
        
        return "\n".join(lines)
    
    def _format_chart_analysis(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format complete chart analysis including patterns, support/resistance, and trends."""
        symbol = data.get("symbol", "Unknown")
        period = data.get("period", "Unknown")
        
        lines = [
            f"Chart Analysis for {symbol}",
            f"Period: {format_time_period(period)}",
            ""
        ]
        
        # Support and Resistance
        support_resistance = data.get("support_resistance", {})
        if support_resistance:
            lines.extend([
                "Support & Resistance Levels:",
                f"  Nearest Support: {format_currency(support_resistance.get('nearest_support', 0)) if support_resistance.get('nearest_support') else 'None'}",
                f"  Nearest Resistance: {format_currency(support_resistance.get('nearest_resistance', 0)) if support_resistance.get('nearest_resistance') else 'None'}",
                ""
            ])
            
            # List support levels
            support_levels = support_resistance.get("support_levels", [])
            if support_levels:
                lines.append("  Support Levels: " + ", ".join([format_currency(s) for s in support_levels]))
            
            # List resistance levels
            resistance_levels = support_resistance.get("resistance_levels", [])
            if resistance_levels:
                lines.append("  Resistance Levels: " + ", ".join([format_currency(r) for r in resistance_levels]))
            
            lines.append("")
        
        # Trend Analysis
        trend = data.get("trend", {})
        if trend:
            lines.extend([
                "Trend Analysis:",
                f"  Direction: {trend.get('direction', 'Unknown').capitalize()}",
                f"  Strength: {format_percentage(trend.get('strength', 0))}",
                f"  Moving Average Alignment: {trend.get('sma_alignment', 'Unknown').capitalize()}",
                ""
            ])
        
        # Patterns
        patterns = data.get("patterns", [])
        if patterns:
            lines.append("Chart Patterns Detected:")
            for pattern in patterns:
                lines.extend([
                    f"  {pattern.get('description', 'Unknown pattern')}",
                    f"    Confidence: {format_percentage(pattern.get('confidence', 0) * 100)}",
                ])
        else:
            lines.append("No significant chart patterns detected.")
        
        return "\n".join(lines)
    
    def _format_performance_comparison(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format performance comparison between multiple stocks."""
        symbols = data.get("symbols", [])
        period = data.get("period", "Unknown")
        comparison = data.get("comparison", {})
        
        if not comparison:
            return "No comparison data available."
        
        lines = [
            f"Performance Comparison",
            f"Symbols: {', '.join(symbols)}",
            f"Period: {format_time_period(period)}",
            ""
        ]
        
        # Create comparison table
        headers = ["Symbol", "Current", "Return", "Volatility", "Sharpe"]
        rows = []
        
        for symbol in symbols:
            if symbol in comparison and symbol != "correlations":
                stock_data = comparison[symbol]
                metrics = stock_data.get("metrics", {})
                price_data = stock_data.get("price_data", {})
                
                row = [
                    symbol,
                    format_currency(price_data.get("current", 0)),
                    format_percentage(metrics.get("total_return", 0)),
                    format_percentage(metrics.get("volatility", 0)),
                    format_number(metrics.get("sharpe_ratio", 0), 2)
                ]
                rows.append(row)
        
        if rows:
            lines.append(create_table(headers, rows))
        
        # Add correlation matrix if available
        correlations = comparison.get("correlations", {})
        if correlations and len(symbols) > 1:
            lines.extend([
                "",
                "Correlation Matrix:",
            ])
            
            # Create correlation table
            corr_headers = [""] + symbols
            corr_rows = []
            
            for symbol1 in symbols:
                row = [symbol1]
                for symbol2 in symbols:
                    if symbol1 in correlations and symbol2 in correlations[symbol1]:
                        corr_value = correlations[symbol1][symbol2]
                        row.append(format_number(corr_value, 2))
                    else:
                        row.append("N/A")
                corr_rows.append(row)
            
            if corr_rows:
                lines.append(create_table(corr_headers, corr_rows))
        
        return "\n".join(lines)
    
    def _get_rsi_signal(self, rsi_value: float) -> str:
        """Get RSI signal interpretation."""
        if rsi_value >= 70:
            return "(Overbought)"
        elif rsi_value <= 30:
            return "(Oversold)"
        else:
            return "(Neutral)"
    
    def format_empty_response(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Format response when no data is available."""
        symbol = context.get("symbol", "the requested stock") if context else "the requested stock"
        return f"No technical analysis data available for {symbol}."


# Create a singleton instance for use in the server
formatter = TechnicalAnalysisFormatter()