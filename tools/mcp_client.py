import asyncio
import json
from typing import Dict, Any, Optional
import websockets
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self, host: str = "localhost", port: int = 5001):
        self.host = host
        self.port = port
        self.websocket = None
        self.connected = False
    
    async def connect(self):
        """Connect to the MCP server."""
        try:
            self.websocket = await websockets.connect(f"ws://{self.host}:{self.port}")
            self.connected = True
            logger.info(f"Connected to MCP server at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool on the MCP server."""
        if not self.connected:
            await self.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": tool_name,
            "params": kwargs,
            "id": 1
        }
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        
        result = json.loads(response)
        
        if "error" in result:
            raise Exception(f"MCP error: {result['error']}")
        
        return result.get("result", {})
    
    async def close(self):
        """Close the connection."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

class RemoteTool:
    """Wrapper for a remote tool accessed via MCP."""
    
    def __init__(self, tool_id: str, connection: MCPClient, metadata: Dict[str, Any]):
        self.tool_id = tool_id
        self.connection = connection
        self.metadata = metadata
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        return await self.connection.call_tool(self.tool_id, **kwargs)
    
    def get_cost(self) -> float:
        """Get the cost of using this tool."""
        return self.metadata.get("cost", 0.0)
    
    def get_description(self) -> str:
        """Get the tool description."""
        return self.metadata.get("description", "")