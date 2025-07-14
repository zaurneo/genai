import asyncio
import json
from typing import Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self, host: str = "localhost", port: int = 5001):
        self.host = host
        self.port = port
        self.session = None
        self.base_url = None
        self.connected = False
    
    async def connect(self):
        """Connect to the MCP server."""
        try:
            # For HTTP transport, we don't maintain a persistent connection
            # Just verify the server is reachable
            self.session = aiohttp.ClientSession()
            self.base_url = f"http://{self.host}:{self.port}/mcp/"
            self.connected = True
            logger.info(f"MCP client configured for server at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to configure MCP client: {e}")
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
        
        try:
            async with self.session.post(
                self.base_url,
                json=request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error: {response.status}")
                
                result = await response.json()
                
                if "error" in result:
                    raise Exception(f"MCP error: {result['error']}")
                
                return result.get("result", {})
        except aiohttp.ClientError as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def close(self):
        """Close the connection."""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
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