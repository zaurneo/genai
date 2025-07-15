from typing import Dict, List, Any, Optional
import yaml
import asyncio
from pathlib import Path
from functools import lru_cache
import logging
import os

from tools.mcp_client import MCPClient, RemoteTool

logger = logging.getLogger(__name__)

class DynamicToolRegistry:
    """Registry for dynamically loading and managing tools."""
    
    def __init__(self, manifest_path: str = None):
        self.manifest_path = manifest_path or Path(__file__).parent / "tool_manifest.yaml"
        self.manifest = self.load_manifest()
        self.tool_cache = {}
        self.mcp_connections = {}
        self.connection_lock = asyncio.Lock()
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load tool manifest from YAML file."""
        with open(self.manifest_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def load_tools(self, tool_ids: List[str]) -> Dict[str, RemoteTool]:
        """Load multiple tools by their IDs."""
        tasks = [self.get_tool(tool_id) for tool_id in tool_ids]
        tools = await asyncio.gather(*tasks)
        return {tool_id: tool for tool_id, tool in zip(tool_ids, tools)}
    
    async def get_tool(self, tool_id: str) -> RemoteTool:
        """Get a single tool by ID."""
        # Check cache first
        if tool_id in self.tool_cache:
            return self.tool_cache[tool_id]
        
        # Load tool from manifest
        if tool_id not in self.manifest["tools"]:
            raise ValueError(f"Tool {tool_id} not found in manifest")
        
        tool_info = self.manifest["tools"][tool_id]
        server_name = tool_info["server"]
        
        # Get or create MCP connection
        async with self.connection_lock:
            if server_name not in self.mcp_connections:
                self.mcp_connections[server_name] = await self._connect_mcp(server_name)
        
        # Create remote tool wrapper
        tool = RemoteTool(
            tool_id=tool_id,
            connection=self.mcp_connections[server_name],
            metadata=tool_info
        )
        
        # Cache the tool
        self.tool_cache[tool_id] = tool
        
        return tool
    
    async def _connect_mcp(self, server_name: str) -> MCPClient:
        """Connect to an MCP server."""
        server_config = self.manifest["servers"][server_name]
        
        # Check for environment variable overrides for Docker
        env_map = {
            "stock_data": "MCP_STOCK_DATA_URL",
            "technical_analysis": "MCP_TECHNICAL_URL"
        }
        
        host = server_config["host"]
        port = server_config["port"]
        
        if server_name in env_map:
            env_url = os.getenv(env_map[server_name])
            if env_url:
                # Parse host:port from environment variable
                if ":" in env_url:
                    host, port_str = env_url.split(":")
                    port = int(port_str)
                else:
                    host = env_url
        
        client = MCPClient(
            host=host,
            port=port
        )
        
        await client.connect()
        logger.info(f"Connected to MCP server: {server_name}")
        
        return client
    
    async def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tools based on a query."""
        # Simple keyword search for now
        # In production, this would use embeddings and vector search
        results = []
        
        query_lower = query.lower()
        
        for tool_id, tool_info in self.manifest["tools"].items():
            description = tool_info.get("description", "").lower()
            capabilities = " ".join(tool_info.get("capabilities", [])).lower()
            
            if query_lower in description or query_lower in capabilities:
                results.append({
                    "tool_id": tool_id,
                    "score": self._calculate_relevance(query_lower, description, capabilities),
                    **tool_info
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    def _calculate_relevance(self, query: str, description: str, capabilities: str) -> float:
        """Calculate simple relevance score."""
        score = 0.0
        
        # Exact match in description
        if query in description:
            score += 1.0
        
        # Partial matches
        for word in query.split():
            if word in description:
                score += 0.5
            if word in capabilities:
                score += 0.3
        
        return score
    
    async def get_tool_groups(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        groups = {}
        
        for tool_id, tool_info in self.manifest["tools"].items():
            category = tool_info.get("category", "general")
            if category not in groups:
                groups[category] = []
            groups[category].append(tool_id)
        
        return groups
    
    async def cleanup(self):
        """Clean up connections."""
        for connection in self.mcp_connections.values():
            await connection.close()