"""Base formatter class for all MCP tool formatters."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseFormatter(ABC):
    """Base class for all tool formatters.
    
    Provides a consistent interface for formatting tool responses
    and errors into human-readable text.
    """
    
    @abstractmethod
    def format_response(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Format tool response data into human-readable text.
        
        Args:
            data: The raw data from the tool
            context: Optional context information (e.g., original query parameters)
            
        Returns:
            Formatted string suitable for display to users
        """
        pass
    
    @abstractmethod
    def format_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error messages with context.
        
        Args:
            error: The error message
            context: Optional context information (e.g., what was being attempted)
            
        Returns:
            User-friendly error message
        """
        pass
    
    def format_empty_response(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Format response when no data is available.
        
        Args:
            context: Optional context information
            
        Returns:
            User-friendly message about no data
        """
        return "No data available for your request."