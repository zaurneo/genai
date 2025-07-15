"""HTTP wrapper for Technical Analysis MCP Server"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

from tools.mcp_servers.technical_server.server import calculate_indicators, analyze_patterns, compare_performance

app = FastAPI(title="Technical Analysis MCP Server")

class ToolRequest(BaseModel):
    method: str
    params: Dict[str, Any]
    id: int = 1
    jsonrpc: Optional[str] = None

class ToolResponse(BaseModel):
    result: Dict[str, Any]
    id: int = 1

@app.post("/mcp/")
async def handle_mcp_request(request: ToolRequest) -> Dict[str, Any]:
    """Handle MCP tool requests"""
    try:
        # Map method names to functions
        tool_map = {
            "tools/calculate_indicators": calculate_indicators,
            "tools/analyze_patterns": analyze_patterns,
            "tools/compare_performance": compare_performance,
            "calculate_indicators": calculate_indicators,
            "analyze_patterns": analyze_patterns,
            "compare_performance": compare_performance,
            "technical.calculate_indicators": calculate_indicators,
            "technical.analyze_patterns": analyze_patterns,
            "technical.compare_performance": compare_performance,
        }
        
        method_name = request.method
        if method_name not in tool_map:
            # Try extracting just the method name
            if '.' in method_name:
                method_name = method_name.split('.')[-1]
        
        if method_name not in tool_map:
            return {
                "error": {"code": -32601, "message": f"Method {request.method} not found"},
                "id": request.id
            }
        
        # Call the tool function
        result = await tool_map[method_name](**request.params)
        
        # Return JSON-RPC format response
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id
        }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request.id
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)