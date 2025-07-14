"""HTTP wrapper for Technical Analysis MCP Server"""
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

from .technical_server.server import calculate_indicators, analyze_patterns, compare_performance

app = FastAPI(title="Technical Analysis MCP Server")

class ToolRequest(BaseModel):
    method: str
    params: Dict[str, Any]
    id: int = 1

class ToolResponse(BaseModel):
    result: Dict[str, Any]
    id: int = 1

@app.post("/mcp/")
async def handle_mcp_request(request: ToolRequest) -> ToolResponse:
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
        }
        
        method_name = request.method
        if method_name not in tool_map:
            raise HTTPException(status_code=404, detail=f"Method {method_name} not found")
        
        # Call the tool function
        result = await tool_map[method_name](**request.params)
        
        return ToolResponse(result=result, id=request.id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)