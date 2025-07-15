import asyncio
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import logging

from agent.llm_adapter import LLMAdapter
from agent.enhanced_context_manager import EnhancedContextManager
from tools.registry.enhanced_dynamic_loader import EnhancedDynamicToolRegistry
from tools.mcp_client import MCPClient
from tools.registry import TOOL_REGISTRY, get_tool_descriptions_for_prompt

logger = logging.getLogger(__name__)

class GenesisAgent:
    """Main agent class that orchestrates tool loading and execution."""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_adapter = LLMAdapter(provider=llm_provider)
        self.tool_registry = EnhancedDynamicToolRegistry()
        self.context_manager = EnhancedContextManager()
        self.mcp_client = MCPClient()
    
    async def process_request(self, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process a user request and return a response."""
        try:
            # 1. Load conversation context
            context = self.context_manager.get_context(conversation_id)
            context['conversation_id'] = conversation_id
            
            # 2. Analyze query and select tools using the registry
            analysis = await self.analyze_intent(query, context)
            required_tools = await self.determine_tools(analysis)
            
            # 3. If tools are needed, load and execute them
            if required_tools:
                tools = await self.tool_registry.load_tools(required_tools)
                
                # 4. Create and execute plan with selected tools
                plan = await self.create_execution_plan(query, tools, context, analysis)
                results = await self.execute_plan(plan)
                
                # 5. Update context with execution details
                self._update_context_from_execution(conversation_id, analysis, results)
                response = await self.format_response(results)
            else:
                # No tools needed - return a direct response
                response = "I can help you analyze stocks, view technical indicators, check fundamentals, and compare companies. What would you like to know?"
                results = {"no_tools_used": True}
            
            return {
                "response": response,
                "metadata": {
                    "tools_used": required_tools,
                    "execution_time": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "error": True
            }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Generate system prompt with tool registry information."""
        tool_descriptions = get_tool_descriptions_for_prompt()
        context_summary = self.context_manager.get_conversation_summary(context.get('conversation_id', ''))
        
        return f"""
You are Genesis Assistant, a financial analysis expert. You help users with stock market analysis,
technical indicators, and financial data.

AVAILABLE TOOLS:
{tool_descriptions}

CURRENT CONTEXT:
- Last analyzed entity: {context_summary.get('last_entity', 'None')}
- Previous tool used: {context_summary.get('last_tool', 'None')}
- Recent entities: {context_summary.get('recent_entities', [])}

INSTRUCTIONS:
1. Analyze user queries carefully and match them to available tools
2. Use tools ONLY when they clearly match the user's request
3. For ambiguous requests, consider the context to infer intent
4. If no tools match, explain your capabilities instead
"""

    async def analyze_intent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query and select appropriate tools using the registry."""
        prompt = f"""
{self.get_system_prompt(context)}

User Query: {query}

Analyze this query and determine:
1. What tools (if any) should be used to answer this query
2. What parameters each tool needs
3. Your reasoning for the selection

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
    "entities": {{"symbols": [], "time_period": null, "indicators": []}}
}}

If no tools are needed, set tools_to_use to an empty array.
        """
        
        response = await self.llm_adapter.complete(
            prompt,
            response_format="json",
            temperature=0.3
        )
        
        return json.loads(response)
    
    async def determine_tools(self, intent: Dict[str, Any]) -> List[str]:
        """Extract tool IDs from the analysis result."""
        tools_to_use = intent.get('tools_to_use', [])
        tool_ids = []
        
        for tool_config in tools_to_use:
            tool_id = tool_config.get('tool_id')
            if tool_id:
                tool_ids.append(tool_id)
        
        return tool_ids
    
    async def create_execution_plan(self, query: str, tools: Dict[str, Any], context: Dict[str, Any], analysis: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Create an execution plan for the tools."""
        # Extract tool metadata safely
        tool_metadata = []
        
        if isinstance(tools, dict):
            for tool_id, tool in tools.items():
                if hasattr(tool, 'metadata'):
                    tool_metadata.append(tool.metadata)
                else:
                    # Fallback: use the tool_id as minimal metadata
                    tool_metadata.append({"tool_id": tool_id, "description": f"Tool: {tool_id}"})
        
        prompt = f"""
        Create an execution plan for the following query using the available tools:
        
        Query: {query}
        Available Tools: {json.dumps(tool_metadata, indent=2)}
        Context: {json.dumps(context, indent=2)}
        
        Return a JSON array of steps, each with:
        - tool_id: ID of the tool to use
        - parameters: parameters to pass to the tool
        - depends_on: array of step indices this step depends on
        """
        
        response = await self.llm_adapter.complete(
            prompt,
            response_format="json",
            temperature=0.2
        )
        
        return json.loads(response)
    
    async def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the plan and collect results."""
        results = {}
        
        # Handle both plan formats: direct list or dict with 'steps' key
        if isinstance(plan, dict) and 'steps' in plan:
            plan_steps = plan['steps']
        elif isinstance(plan, list):
            plan_steps = plan
        else:
            logger.error(f"Invalid plan format: {type(plan)}")
            return {"error": "Invalid plan format"}
        
        # Group steps by dependency level
        dependency_levels = self._group_by_dependencies(plan_steps)
        
        # Execute each level in parallel
        for level in dependency_levels:
            level_tasks = []
            for step_idx in level:
                step = plan_steps[step_idx]
                task = self._execute_step(step, results)
                level_tasks.append(task)
            
            # Wait for all tasks in this level to complete
            level_results = await asyncio.gather(*level_tasks)
            
            # Store results
            for idx, result in zip(level, level_results):
                results[f"step_{idx}"] = result
        
        return results
    
    async def _execute_step(self, step: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step in the plan."""
        tool_id = step["tool_id"]
        parameters = step["parameters"]
        
        # Substitute any references to previous results
        parameters = self._substitute_references(parameters, previous_results)
        
        # Get the tool
        tool = await self.tool_registry.get_tool(tool_id)
        
        # Execute the tool
        result = await tool.execute(**parameters)
        
        return result
    
    def _group_by_dependencies(self, plan: List[Dict[str, Any]]) -> List[List[int]]:
        """Group steps by dependency level for parallel execution."""
        levels = []
        processed = set()
        
        while len(processed) < len(plan):
            current_level = []
            
            for idx, step in enumerate(plan):
                if idx in processed:
                    continue
                
                # Check if all dependencies are processed
                deps = step.get("depends_on", [])
                if all(dep in processed for dep in deps):
                    current_level.append(idx)
            
            levels.append(current_level)
            processed.update(current_level)
        
        return levels
    
    def _substitute_references(self, parameters: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute references to previous results in parameters."""
        def substitute(obj):
            if isinstance(obj, str) and obj.startswith("$"):
                # This is a reference to a previous result
                ref = obj[1:]  # Remove $
                return results.get(ref, obj)
            elif isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(item) for item in obj]
            return obj
        
        return substitute(parameters)
    
    def _update_context_from_execution(self, conversation_id: str, analysis: Dict[str, Any], results: Dict[str, Any]):
        """Update context based on what was executed."""
        updates = {}
        
        # Extract entities from the analysis
        entities = analysis.get('entities', {})
        if 'symbols' in entities and entities['symbols']:
            updates['last_entity'] = entities['symbols'][0]
            updates['recent_entities'] = entities['symbols']
        
        # Track tool usage
        tools_used = analysis.get('tools_to_use', [])
        if tools_used:
            updates['last_tool'] = tools_used[0].get('tool_key')
        
        # Update the context
        self.context_manager.update(conversation_id, analysis.get('query', ''), updates)
    
    async def format_response(self, results: Dict[str, Any]) -> str:
        """Format the results into a human-readable response."""
        prompt = f"""
        Format the following analysis results into a clear, concise response:
        
        Results: {json.dumps(results, indent=2)}
        
        Guidelines:
        - Start with a summary of key findings
        - Use bullet points for important metrics
        - Include specific numbers and percentages
        - Provide actionable insights
        - End with a recommendation if applicable
        """
        
        response = await self.llm_adapter.complete(prompt, temperature=0.7)
        return response
    
    async def process_request_stream(self, query: str, conversation_id: str):
        """Process request with streaming response."""
        context = self.context_manager.get_context(conversation_id)
        context['conversation_id'] = conversation_id
        
        yield {"type": "status", "message": "Analyzing your query..."}
        
        analysis = await self.analyze_intent(query, context)
        required_tools = await self.determine_tools(analysis)
        
        if required_tools:
            yield {"type": "status", "message": f"Using {len(required_tools)} tools to gather data..."}
            
            tools = await self.tool_registry.load_tools(required_tools)
            
            yield {"type": "status", "message": "Creating execution plan..."}
            plan = await self.create_execution_plan(query, tools, context, analysis)
            
            yield {"type": "status", "message": "Executing analysis..."}
            results = await self.execute_plan(plan)
            
            # Update context
            self._update_context_from_execution(conversation_id, analysis, results)
            
            # Stream the formatted response
            prompt = await self._create_format_prompt(results)
            async for chunk in self.llm_adapter.complete_stream(prompt, temperature=0.7):
                yield {"type": "content", "chunk": chunk}
        else:
            # No tools needed - yield direct response
            yield {"type": "content", "chunk": "I can help you analyze stocks, view technical indicators, check fundamentals, and compare companies. What would you like to know?"}
    
    async def _create_format_prompt(self, results: Dict[str, Any]) -> str:
        """Create a prompt for formatting the results."""
        return f"""
Format the following analysis results into a clear, professional response:

Results: {json.dumps(results, indent=2)}

Guidelines:
- Be concise and focus on the key findings
- Use specific numbers and data points
- Format numbers appropriately (e.g., $45.23, +2.5%)
- Provide actionable insights where relevant
"""