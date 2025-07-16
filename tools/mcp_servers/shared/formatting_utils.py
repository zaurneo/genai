"""Shared formatting utilities for all MCP tools."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import locale


def format_number(value: float, decimals: int = 2) -> str:
    """Format numbers with commas and decimal places.
    
    Args:
        value: The number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string (e.g., "1,234.56")
    """
    try:
        if decimals == 0:
            return f"{int(value):,}"
        return f"{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: float, decimals: int = 2, multiply: bool = False) -> str:
    """Format as percentage with % sign.
    
    Args:
        value: The percentage value
        decimals: Number of decimal places
        multiply: If True, multiply by 100 (for 0.05 -> 5%)
        
    Returns:
        Formatted percentage string (e.g., "5.25%")
    """
    try:
        if multiply:
            value = value * 100
        return f"{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return f"{value}%"


def format_currency(value: float, currency: str = "USD", decimals: int = 2) -> str:
    """Format as currency with symbol.
    
    Args:
        value: The monetary value
        currency: Currency code (USD, EUR, etc.)
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
    }
    
    symbol = symbols.get(currency, currency + " ")
    formatted_value = format_number(value, decimals)
    
    if currency == "JPY":  # Japanese Yen typically doesn't use decimals
        formatted_value = format_number(value, 0)
    
    return f"{symbol}{formatted_value}"


def format_date(date_str: str, input_format: str = "%Y-%m-%d", output_format: str = "%b %d, %Y") -> str:
    """Format date strings.
    
    Args:
        date_str: The date string to format
        input_format: The format of the input date string
        output_format: The desired output format
        
    Returns:
        Formatted date string (e.g., "Jan 15, 2025")
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except (ValueError, TypeError):
        return date_str


def format_change(current: float, previous: float, show_percentage: bool = True) -> str:
    """Format price/value change with amount and percentage.
    
    Args:
        current: Current value
        previous: Previous value
        show_percentage: Whether to include percentage change
        
    Returns:
        Formatted change string (e.g., "+5.25 (+2.50%)")
    """
    try:
        change = current - previous
        change_pct = (change / previous) * 100 if previous != 0 else 0
        
        sign = "+" if change >= 0 else ""
        change_str = f"{sign}{format_number(change)}"
        
        if show_percentage:
            change_str += f" ({sign}{format_percentage(change_pct)})"
        
        return change_str
    except (ValueError, TypeError, ZeroDivisionError):
        return "N/A"


def format_large_number(value: float) -> str:
    """Format large numbers with K, M, B, T suffixes.
    
    Args:
        value: The number to format
        
    Returns:
        Formatted string (e.g., "1.5M", "2.3B")
    """
    try:
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        
        if abs_value >= 1e12:
            return f"{sign}{abs_value/1e12:.2f}T"
        elif abs_value >= 1e9:
            return f"{sign}{abs_value/1e9:.2f}B"
        elif abs_value >= 1e6:
            return f"{sign}{abs_value/1e6:.2f}M"
        elif abs_value >= 1e3:
            return f"{sign}{abs_value/1e3:.2f}K"
        else:
            return f"{sign}{abs_value:.2f}"
    except (ValueError, TypeError):
        return str(value)


def format_time_period(period: str) -> str:
    """Convert period codes to human-readable format.
    
    Args:
        period: Period code (e.g., "1d", "1mo", "1y")
        
    Returns:
        Human-readable period (e.g., "1 day", "1 month", "1 year")
    """
    period_map = {
        "1d": "1 day",
        "5d": "5 days",
        "1mo": "1 month",
        "3mo": "3 months",
        "6mo": "6 months",
        "1y": "1 year",
        "2y": "2 years",
        "5y": "5 years",
        "10y": "10 years",
        "ytd": "year to date",
        "max": "all time"
    }
    
    return period_map.get(period, period)


def create_table(headers: List[str], rows: List[List[str]], max_width: int = 80) -> str:
    """Create a simple ASCII table.
    
    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of values)
        max_width: Maximum table width
        
    Returns:
        Formatted ASCII table
    """
    if not headers or not rows:
        return ""
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Build table
    lines = []
    
    # Header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-" * min(len(header_line), max_width))
    
    # Rows
    for row in rows:
        row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row[:len(headers)]))
        lines.append(row_line)
    
    return "\n".join(lines)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix