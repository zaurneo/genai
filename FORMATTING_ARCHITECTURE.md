# Formatting Architecture Guide

## Overview
This document describes the architecture for formatting tool responses in the Genesis AI system. The system uses a hybrid approach where tools provide formatted responses when possible, with LLM-based formatting as a fallback.

## Current Architecture

### 1. Tool-Level Formatting (Primary)
- Each MCP tool includes formatting logic to convert raw data into human-readable text
- Tools return both raw data and formatted responses
- Located in: Individual server files (e.g., `tools/mcp_servers/stock_data_server/server.py`)

### 2. Agent-Level Formatting (Fallback)
- The agent checks for formatted responses from tools
- If no formatting is provided, uses LLM to format the raw data
- Located in: `agent/enhanced_genesis_agent.py`

## Recommended Architecture

### Directory Structure
```
tools/
├── mcp_servers/
│   ├── stock_data_server/
│   │   ├── server.py          # MCP server implementation
│   │   ├── yahoo_client.py    # Data fetching logic
│   │   └── formatters.py      # Formatting functions (NEW)
│   ├── technical_server/
│   │   ├── server.py
│   │   └── formatters.py      # Formatting functions (NEW)
│   └── shared/
│       ├── __init__.py
│       ├── base_formatter.py  # Base formatter class (NEW)
│       └── formatting_utils.py # Shared formatting utilities (NEW)
```

### Component Responsibilities

#### 1. Base Formatter (`tools/mcp_servers/shared/base_formatter.py`)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseFormatter(ABC):
    """Base class for all tool formatters"""
    
    @abstractmethod
    def format_response(self, data: Dict[str, Any]) -> str:
        """Format tool response data into human-readable text"""
        pass
    
    @abstractmethod
    def format_error(self, error: str, context: Dict[str, Any]) -> str:
        """Format error messages with context"""
        pass
```

#### 2. Tool-Specific Formatters (`tools/mcp_servers/{tool}/formatters.py`)
```python
from tools.mcp_servers.shared.base_formatter import BaseFormatter
from tools.mcp_servers.shared.formatting_utils import format_number, format_percentage

class StockDataFormatter(BaseFormatter):
    def format_response(self, data: Dict[str, Any]) -> str:
        # Tool-specific formatting logic
        pass
    
    def format_error(self, error: str, context: Dict[str, Any]) -> str:
        # Tool-specific error formatting
        pass
```

#### 3. Shared Utilities (`tools/mcp_servers/shared/formatting_utils.py`)
```python
def format_number(value: float, decimals: int = 2) -> str:
    """Format numbers with commas and decimal places"""
    pass

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format as percentage with % sign"""
    pass

def format_currency(value: float, currency: str = "USD") -> str:
    """Format as currency with symbol"""
    pass

def format_date(date_str: str, format: str = "MMM DD, YYYY") -> str:
    """Format date strings"""
    pass
```

## Implementation Guidelines

### For Tool Developers

1. **Create a formatter module** for each MCP server
   - Inherit from `BaseFormatter`
   - Implement tool-specific formatting logic
   - Use shared utilities for common formatting needs

2. **In the server file**:
   ```python
   from .formatters import StockDataFormatter
   
   formatter = StockDataFormatter()
   
   @mcp.tool(description="Get stock price")
   async def get_price(symbol: str, period: str = "1d"):
       # Fetch data...
       
       # Format response
       formatted = formatter.format_response(data)
       
       return {
           "data": data,
           "formatted": formatted
       }
   ```

3. **Error handling**:
   ```python
   except Exception as e:
       formatted_error = formatter.format_error(str(e), {
           "symbol": symbol,
           "period": period
       })
       return {
           "error": str(e),
           "formatted": formatted_error
       }
   ```

### For Agent Developers

1. **Check for formatted responses first**:
   ```python
   if "formatted" in result:
       return result["formatted"]
   ```

2. **Use LLM fallback for unformatted responses**:
   ```python
   if needs_llm_formatting:
       return await self._format_with_llm(results, query)
   ```

## Benefits of This Architecture

1. **Separation of Concerns**: Formatting logic is separate from business logic
2. **Reusability**: Shared utilities reduce code duplication
3. **Testability**: Formatters can be unit tested independently
4. **Maintainability**: Easy to update formatting without touching server logic
5. **Extensibility**: New tools can easily adopt the formatting pattern
6. **Consistency**: Base class ensures consistent interface across tools

## Migration Path

1. **Phase 1**: Create shared formatting infrastructure
   - Create base formatter class
   - Create shared utilities module
   - Document formatting guidelines

2. **Phase 2**: Migrate existing tools
   - Extract formatting functions from server files
   - Create formatter modules for each tool
   - Update server files to use formatters

3. **Phase 3**: Update documentation
   - Update tool development guide
   - Add formatter examples
   - Create formatting best practices

## Best Practices

1. **Keep formatters stateless**: They should be pure functions
2. **Handle edge cases**: Empty data, null values, etc.
3. **Be concise**: Format for command-line readability
4. **Use consistent patterns**: Similar data should be formatted similarly
5. **Test thoroughly**: Include unit tests for all formatters
6. **Document format examples**: Show input/output examples in docstrings

## Example Implementation

See `tools/mcp_servers/stock_data_server/formatters.py` for a complete example of a well-structured formatter module.