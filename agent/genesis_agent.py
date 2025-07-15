import asyncio
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import logging

from agent.llm_adapter import LLMAdapter
from agent.context_manager import ContextManager
from tools.registry.dynamic_loader import DynamicToolRegistry
from tools.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class GenesisAgent:
    """Main agent class that orchestrates tool loading and execution."""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_adapter = LLMAdapter(provider=llm_provider)
        self.tool_registry = DynamicToolRegistry()
        self.context_manager = ContextManager()
        self.mcp_client = MCPClient()
    
    async def process_request(self, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process a user request and return a response."""
        try:
            # 1. Load conversation context
            context = self.context_manager.get_context(conversation_id)
            
            # 2. Analyze intent and determine required tools
            intent = await self.analyze_intent(query, context)
            required_tools = await self.determine_tools(intent)
            
            # 3. Load tools dynamically via MCP
            tools = await self.tool_registry.load_tools(required_tools)
            
            # 4. Create and execute plan
            plan = await self.create_execution_plan(query, tools, context)
            results = await self.execute_plan(plan)
            
            # 5. Update context and return response
            self.context_manager.update(conversation_id, query, results)
            response = await self.format_response(results)
            
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
    
    async def analyze_intent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent using LLM."""
        prompt = f"""
        Analyze the following query and determine the user's intent:
        
        Query: {query}
        Context: {json.dumps(context, indent=2)}
        
        Return a JSON object with:
        - intent: main purpose (analyze_stock, compare_stocks, technical_analysis, etc.)
        - entities: extracted entities (stock symbols, time periods, indicators)
        - confidence: confidence score (0-1)
        """
        
        response = await self.llm_adapter.complete(
            prompt,
            response_format="json",
            temperature=0.3
        )
        
        return json.loads(response)
    
    async def determine_tools(self, intent: Dict[str, Any]) -> List[str]:
        """Determine which tools are needed based on intent."""
        intent_to_tools = {
            "analyze_stock": ["stock_data.get_price", "stock_data.get_fundamentals", "technical.calculate_indicators"],
            "compare_stocks": ["stock_data.get_price", "stock_data.get_fundamentals", "technical.compare_performance"],
            "technical_analysis": ["stock_data.get_price", "technical.calculate_indicators", "technical.analyze_patterns"],
            "fundamental_analysis": ["stock_data.get_fundamentals", "stock_data.get_financials"]
        }
        
        base_tools = intent_to_tools.get(intent["intent"], ["stock_data.get_price"])
        
        # Add specific tools based on entities
        if "indicators" in intent.get("entities", {}):
            base_tools.append("technical.calculate_indicators")
        
        return list(set(base_tools))
    
    async def create_execution_plan(self, query: str, tools: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        # Similar to process_request but yields chunks
        context = self.context_manager.get_context(conversation_id)
        
        # Yield status updates
        yield {"type": "status", "message": "Analyzing your query..."}
        
        intent = await self.analyze_intent(query, context)
        yield {"type": "status", "message": "Loading required tools..."}
        
        required_tools = await self.determine_tools(intent)
        tools = await self.tool_registry.load_tools(required_tools)
        
        yield {"type": "status", "message": "Creating execution plan..."}
        plan = await self.create_execution_plan(query, tools, context)
        
        yield {"type": "status", "message": "Executing analysis..."}
        results = await self.execute_plan(plan)
        
        # Stream the formatted response
        async for chunk in self.llm_adapter.complete_stream(
            await self._create_format_prompt(results),
            temperature=0.7
        ):
            yield {"type": "content", "chunk": chunk}
        
        # Update context
        self.context_manager.update(conversation_id, query, results)