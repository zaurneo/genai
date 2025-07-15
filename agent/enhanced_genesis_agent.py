import asyncio
from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime
import logging

from agent.llm_adapter import LLMAdapter
from agent.context_manager import ContextManager
from tools.registry.dynamic_loader import DynamicToolRegistry
from tools.mcp_client import MCPClient
from tools.registry import TOOL_REGISTRY, get_tool_descriptions_for_prompt, CONTEXT_HINTS

logger = logging.getLogger(__name__)

class EnhancedGenesisAgent:
    """Enhanced agent that uses tool registry for intelligent tool selection."""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_adapter = LLMAdapter(provider=llm_provider)
        self.tool_registry = DynamicToolRegistry()
        self.context_manager = ContextManager()
        self.mcp_client = MCPClient()
        
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Generate system prompt with tool registry information."""
        tool_descriptions = get_tool_descriptions_for_prompt()
        
        return f"""
You are Genesis Assistant, a financial analysis expert. You help users with stock market analysis, 
technical indicators, and financial data.

AVAILABLE TOOLS:
{tool_descriptions}

CURRENT CONTEXT:
- Last analyzed entity: {context.get('last_entity', 'None')}
- Previous tool used: {context.get('last_tool', 'None')}
- Conversation topic: {context.get('topic', 'None')}
- Recent entities: {context.get('recent_entities', [])}

INSTRUCTIONS:
1. Analyze user queries carefully and match them to available tools based on the "when_to_use" descriptions
2. Use tools ONLY when they clearly match the user's request
3. For ambiguous requests, consider the context to infer intent
4. If no tools match, explain your capabilities instead of defaulting to any tool
5. Always have a clear reason for selecting each tool
6. You can use multiple tools in sequence if needed to fully answer the user's question

AMBIGUOUS QUERY HANDLING:
- "What about it?" → Check context for last entity and determine what aspect to analyze
- "How about last year?" → Apply time period modification to previous query type
- "Compare with the other one" → Use recent_entities from context
- "Why did it change?" → This would need news/event analysis (not available yet)

CRITICAL: Never use a tool just because it exists. Only use tools that directly address the user's request.
"""

    async def process_request(self, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process a user request using enhanced tool selection."""
        try:
            # 1. Load conversation context
            context = self.context_manager.get_context(conversation_id)
            
            # 2. Let the agent analyze and select tools
            analysis = await self.analyze_with_tools(query, context)
            
            # 3. Execute selected tools if any
            if analysis.get('tools_to_use'):
                results = await self.execute_tools(analysis['tools_to_use'], context)
                
                # 4. Update context with what was done
                self._update_context_from_execution(conversation_id, analysis, results)
                
                # 5. Format final response
                response = await self.format_response(results, query)
            else:
                # No tools needed - use the agent's direct response
                response = analysis.get('response', "I understand your question but don't have the right tools to help with that.")
            
            return {
                "response": response,
                "metadata": {
                    "tools_used": analysis.get('tools_to_use', []),
                    "reasoning": analysis.get('reasoning', ''),
                    "execution_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "error": True
            }
    
    async def analyze_with_tools(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Let the agent analyze the query and select appropriate tools."""
        prompt = f"""
{self.get_system_prompt(context)}

User Query: {query}

Analyze this query and determine:
1. What tools (if any) should be used to answer this query
2. What parameters each tool needs
3. The order of execution if multiple tools are needed
4. Your reasoning for the selection

Return a JSON object with:
{{
    "tools_to_use": [
        {{
            "tool_key": "tool_name_from_registry",
            "tool_id": "actual_tool_id",
            "parameters": {{}},
            "reason": "why this tool is needed"
        }}
    ],
    "reasoning": "overall reasoning for tool selection",
    "response": "direct response if no tools are needed"
}}

If the query doesn't require any tools (like "What can you do?"), set tools_to_use to an empty array 
and provide a helpful response in the "response" field.
"""
        
        response = await self.llm_adapter.complete(
            prompt,
            response_format="json",
            temperature=0.3
        )
        
        return json.loads(response)
    
    async def execute_tools(self, tool_configs: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the selected tools."""
        results = {}
        
        for i, config in enumerate(tool_configs):
            tool_id = config['tool_id']
            parameters = config['parameters']
            
            # Resolve any context-based parameters
            parameters = self._resolve_parameters(parameters, context)
            
            # Load and execute tool
            tool = await self.tool_registry.get_tool(tool_id)
            result = await tool.execute(**parameters)
            
            results[f"tool_{i}_{config['tool_key']}"] = {
                "result": result,
                "tool_used": tool_id,
                "reason": config.get('reason', '')
            }
        
        return results
    
    def _resolve_parameters(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameters that might reference context."""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$context."):
                # This is a context reference
                context_key = value.replace("$context.", "")
                resolved[key] = context.get(context_key, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _update_context_from_execution(self, conversation_id: str, analysis: Dict[str, Any], results: Dict[str, Any]):
        """Update context based on what was executed."""
        updates = {}
        
        # Track entities mentioned
        for tool_config in analysis.get('tools_to_use', []):
            params = tool_config.get('parameters', {})
            
            # Track stock symbols
            if 'symbol' in params:
                updates['last_entity'] = params['symbol']
                recent = self.context_manager.get_context(conversation_id).get('recent_entities', [])
                if params['symbol'] not in recent:
                    recent.append(params['symbol'])
                updates['recent_entities'] = recent[-5:]  # Keep last 5
                
            # Track tool usage
            updates['last_tool'] = tool_config['tool_key']
        
        # Update conversation topic if we can infer it
        if 'technical' in str(analysis.get('tools_to_use', [])):
            updates['topic'] = 'technical_analysis'
        elif 'fundamental' in str(analysis.get('tools_to_use', [])):
            updates['topic'] = 'fundamental_analysis'
        
        self.context_manager.update(conversation_id, analysis.get('query', ''), updates)
    
    async def format_response(self, results: Dict[str, Any], original_query: str) -> str:
        """Format the results into a human-readable response."""
        # Extract just the result data for formatting
        result_data = {}
        for key, value in results.items():
            result_data[key] = value.get('result', value)
        
        prompt = f"""
Format the following analysis results into a clear, professional response for the user's query:

User Query: {original_query}
Results: {json.dumps(result_data, indent=2)}

Guidelines:
- Be concise and focus on answering the user's specific question
- Use numbers and specific data points from the results
- Format numbers appropriately (e.g., $45.23, +2.5%, Market Cap: $2.1T)
- If multiple tools were used, integrate the results naturally
- Don't mention tool names or technical details about how you got the data
"""
        
        response = await self.llm_adapter.complete(prompt, temperature=0.7)
        return response
    
    async def process_request_stream(self, query: str, conversation_id: str):
        """Process request with streaming response."""
        context = self.context_manager.get_context(conversation_id)
        
        yield {"type": "status", "message": "Analyzing your query..."}
        
        analysis = await self.analyze_with_tools(query, context)
        
        if analysis.get('tools_to_use'):
            yield {"type": "status", "message": f"Using {len(analysis['tools_to_use'])} tools to gather data..."}
            
            results = await self.execute_tools(analysis['tools_to_use'], context)
            self._update_context_from_execution(conversation_id, analysis, results)
            
            yield {"type": "status", "message": "Formatting response..."}
            
            # Stream the final response
            response = await self.format_response(results, query)
            yield {"type": "response", "content": response}
        else:
            yield {"type": "response", "content": analysis.get('response', "I don't have the right tools for that request.")}