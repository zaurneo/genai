from typing import Dict, List, Any, Optional, Tuple
import yaml
import asyncio
from pathlib import Path
from functools import lru_cache
import logging
import os

from tools.mcp_client import MCPClient, RemoteTool
from tools.registry import TOOL_REGISTRY, TOOL_CATEGORIES, get_tools_by_category

logger = logging.getLogger(__name__)

class EnhancedDynamicToolRegistry:
    """Enhanced registry that bridges the tool registry with dynamic loading."""
    
    def __init__(self, manifest_path: str = None):
        self.manifest_path = manifest_path or Path(__file__).parent / "tool_manifest.yaml"
        self.manifest = self.load_manifest()
        self.tool_cache = {}
        self.mcp_connections = {}
        self.connection_lock = asyncio.Lock()
        
        # Map registry keys to actual tool IDs
        self.registry_to_tool_id = self._build_registry_mapping()
    
    def load_manifest(self) -> Dict[str, Any]:
        """Load tool manifest from YAML file."""
        with open(self.manifest_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _build_registry_mapping(self) -> Dict[str, str]:
        """Build mapping from registry keys to actual tool IDs."""
        mapping = {}
        for key, info in TOOL_REGISTRY.items():
            mapping[key] = info['id']
        return mapping
    
    async def load_tools_from_registry(self, registry_keys: List[str]) -> Dict[str, RemoteTool]:
        """Load tools using registry keys instead of direct tool IDs."""
        tool_ids = []
        key_to_id_map = {}
        
        for key in registry_keys:
            if key in self.registry_to_tool_id:
                tool_id = self.registry_to_tool_id[key]
                tool_ids.append(tool_id)
                key_to_id_map[key] = tool_id
            else:
                logger.warning(f"Registry key '{key}' not found in mapping")
        
        # Load the actual tools
        loaded_tools = await self.load_tools(tool_ids)
        
        # Return with registry keys
        result = {}
        for key, tool_id in key_to_id_map.items():
            if tool_id in loaded_tools:
                result[key] = loaded_tools[tool_id]
        
        return result
    
    async def load_tools(self, tool_ids: List[str]) -> Dict[str, RemoteTool]:
        """Load multiple tools by their IDs."""
        tasks = [self.get_tool(tool_id) for tool_id in tool_ids]
        tools = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for tool_id, tool in zip(tool_ids, tools):
            if isinstance(tool, Exception):
                logger.error(f"Failed to load tool {tool_id}: {tool}")
            else:
                result[tool_id] = tool
        
        return result
    
    async def get_tool(self, tool_id: str) -> RemoteTool:
        """Get a single tool by ID with enhanced metadata."""
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
        
        # Find registry info for enhanced metadata
        registry_info = None
        for key, info in TOOL_REGISTRY.items():
            if info['id'] == tool_id:
                registry_info = info
                break
        
        # Merge manifest and registry metadata
        enhanced_metadata = {
            **tool_info,
            "registry_key": next((k for k, v in self.registry_to_tool_id.items() if v == tool_id), None),
            "when_to_use": registry_info.get("when_to_use") if registry_info else None,
            "examples": registry_info.get("examples") if registry_info else None
        }
        
        # Create remote tool wrapper
        tool = RemoteTool(
            tool_id=tool_id,
            connection=self.mcp_connections[server_name],
            metadata=enhanced_metadata
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
    
    async def search_tools_enhanced(self, query: str, context: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Enhanced tool search that uses registry information."""
        results = []
        query_lower = query.lower()
        
        for registry_key, registry_info in TOOL_REGISTRY.items():
            score = 0.0
            
            # Check description
            if query_lower in registry_info['description'].lower():
                score += 1.0
            
            # Check when_to_use
            if query_lower in registry_info['when_to_use'].lower():
                score += 0.8
            
            # Check examples
            for example in registry_info.get('examples', []):
                if query_lower in example.lower():
                    score += 0.6
                    break
            
            # Context bonus
            if context:
                if context.get('last_tool') == registry_key:
                    score += 0.3  # Slight preference for recently used tool
                
                # Check if query relates to last entity
                last_entity = context.get('last_entity')
                if last_entity and last_entity.lower() in query_lower:
                    score += 0.4
            
            if score > 0:
                results.append({
                    "registry_key": registry_key,
                    "tool_id": registry_info['id'],
                    "score": score,
                    "description": registry_info['description'],
                    "when_to_use": registry_info['when_to_use']
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    async def get_tools_for_category(self, category: str) -> Dict[str, RemoteTool]:
        """Load all tools in a specific category."""
        category_tools = get_tools_by_category(category)
        
        if not category_tools:
            logger.warning(f"No tools found for category: {category}")
            return {}
        
        # Get tool IDs for the category
        tool_ids = [info['id'] for info in category_tools.values()]
        
        return await self.load_tools(tool_ids)
    
    async def get_tool_suggestions(self, partial_query: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get tool suggestions for autocomplete or hints."""
        suggestions = []
        partial_lower = partial_query.lower()
        
        for key, info in TOOL_REGISTRY.items():
            # Check if partial query matches beginning of examples
            for example in info.get('examples', []):
                if example.lower().startswith(partial_lower):
                    suggestions.append({
                        "suggestion": example,
                        "tool": key,
                        "description": info['description']
                    })
        
        # Limit suggestions
        return suggestions[:5]
    
    async def cleanup(self):
        """Clean up MCP connections."""
        for connection in self.mcp_connections.values():
            await connection.disconnect()
        self.mcp_connections.clear()
        self.tool_cache.clear()

# Utility functions for migration
def map_old_tool_id_to_registry_key(tool_id: str) -> Optional[str]:
    """Map an old tool ID to its registry key."""
    for key, info in TOOL_REGISTRY.items():
        if info['id'] == tool_id:
            return key
    return None

def get_registry_info_for_tool(tool_id: str) -> Optional[Dict[str, Any]]:
    """Get registry information for a tool ID."""
    for key, info in TOOL_REGISTRY.items():
        if info['id'] == tool_id:
            return {"registry_key": key, **info}
    return None