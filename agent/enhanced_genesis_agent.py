from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import BaseOutputParser
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import re
import asyncio
from datetime import datetime
import logging
import json

from agent.llm_adapter import LLMAdapter
from agent.enhanced_context_manager import EnhancedContextManager
from tools.registry.enhanced_dynamic_loader import EnhancedDynamicToolRegistry
from tools.mcp_client import MCPClient
from tools.registry import TOOL_REGISTRY, get_tool_descriptions_for_prompt

logger = logging.getLogger(__name__)

# Define structured output models
class StockEntity(BaseModel):
    symbols: List[str] = Field(default_factory=list, description="Stock ticker symbols mentioned")
    time_period: str = Field(default="1mo", description="Time period for analysis")
    indicators: List[str] = Field(default_factory=list, description="Technical indicators requested")
    
    @validator('symbols')
    def uppercase_symbols(cls, v):
        return [s.upper() for s in v]

class IntentAnalysis(BaseModel):
    intent: str = Field(description="Main intent: analyze_stock, compare_stocks, technical_analysis, fundamental_analysis")
    entities: StockEntity
    confidence: float = Field(ge=0, le=1, description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Brief explanation of the intent classification")
    required_tools: List[str] = Field(default_factory=list, description="Tools needed for this request")

class ToolParameters(BaseModel):
    tool_name: str = Field(description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(description="Parameters for the tool")
    
class ExecutionPlan(BaseModel):
    steps: List[ToolParameters] = Field(description="Ordered list of tool executions")
    description: str = Field(description="Brief description of the execution plan")

class EnhancedGenesisAgent:
    """Genesis Agent enhanced with LangChain for structured outputs and better prompt management."""
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_adapter = LLMAdapter(provider=llm_provider)
        self.tool_registry = EnhancedDynamicToolRegistry()
        self.context_manager = EnhancedContextManager()
        self.mcp_client = MCPClient()
        
        # Initialize LangChain components
        self.setup_chains()
    
    def setup_chains(self):
        """Initialize LangChain components for structured output parsing."""
        # Create output parser with automatic fixing
        parser = PydanticOutputParser(pydantic_object=IntentAnalysis)
        self.intent_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm_adapter.llm)
        
        # Create sophisticated prompt template for intent analysis
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a financial analysis intent classifier. 
            Analyze user queries and extract their intent and entities.
            
            Possible intents:
            - analyze_stock: Single stock analysis
            - compare_stocks: Multiple stock comparison
            - technical_analysis: Technical indicators focus
            - fundamental_analysis: Company fundamentals focus
            - market_overview: Broad market analysis
            
            Available tools: {available_tools}
            
            {format_instructions}"""),
            ("human", "Query: {query}\nConversation Context: {context}")
        ])
        
        # Create execution plan parser
        plan_parser = PydanticOutputParser(pydantic_object=ExecutionPlan)
        self.plan_parser = OutputFixingParser.from_llm(parser=plan_parser, llm=self.llm_adapter.llm)
        
        # Create execution plan prompt
        self.plan_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a financial analysis execution planner.
            Create a step-by-step plan using available tools.
            
            CRITICAL PARAMETER RULES - YOU MUST FOLLOW THESE EXACTLY:
            
            For stock_analyzer tool, the parameters MUST be:
            - "symbol": string (single stock symbol, NOT "symbols")  
            - "period": string (time period like "1d", "1mo", NOT "time_period")
            
            NEVER use these parameter names:
            - "symbols" (use "symbol" instead)
            - "time_period" (use "period" instead)
            
            Example correct parameters for stock_analyzer:
            {{"symbol": "AAPL", "period": "1d"}}
            
            Available tools with descriptions:
            {tool_descriptions}
            
            {format_instructions}"""),
            ("human", "Intent: {intent}\nEntities: {entities}\nQuery: {query}")
        ])
        
        # Create chains without output_parser to avoid double parsing
        self.intent_chain = LLMChain(
            llm=self.llm_adapter.llm,
            prompt=self.intent_prompt
        )
        
        self.plan_chain = LLMChain(
            llm=self.llm_adapter.llm,
            prompt=self.plan_prompt
        )
    
    async def analyze_intent_enhanced(self, query: str, context: Dict[str, Any]) -> IntentAnalysis:
        """Enhanced intent analysis with guaranteed structured output."""
        # Extract context summary instead of dumping everything
        context_summary = self._summarize_context(context)
        
        # Get available tools
        available_tools = list(TOOL_REGISTRY.keys())
        
        try:
            # Run the chain
            result = await self.intent_chain.ainvoke({
                "query": query,
                "context": context_summary,
                "available_tools": ", ".join(available_tools),
                "format_instructions": self.intent_parser.get_format_instructions()
            })
            
            # Debug logging
            logger.debug(f"Chain result type: {type(result)}")
            logger.debug(f"Chain result: {result}")
            
            # Check if result is already an IntentAnalysis object
            if isinstance(result, IntentAnalysis):
                return result
            
            # Extract text from result and parse it
            if isinstance(result, dict) and 'text' in result:
                text_output = result['text']
            elif isinstance(result, str):
                text_output = result
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
            
            # Parse the text output
            return self.intent_parser.parse(text_output)
            
        except Exception as e:
            logger.warning(f"Intent analysis failed, using fallback: {e}")
            # Fallback with regex extraction
            return self._fallback_intent_extraction(query)
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Create a relevant summary of conversation context."""
        messages = context.get("messages", [])
        if not messages:
            return "No previous context"
        
        # Get last 3 relevant messages
        recent_messages = messages[-3:]
        summary_parts = []
        
        for msg in recent_messages:
            if "query" in msg:
                summary_parts.append(f"Previous query: {msg['query']}")
            if "results" in msg and "symbols" in msg["results"]:
                summary_parts.append(f"Previously analyzed: {msg['results']['symbols']}")
        
        return " | ".join(summary_parts)
    
    def _fallback_intent_extraction(self, query: str) -> IntentAnalysis:
        """Regex-based fallback for intent extraction."""
        # Extract stock symbols
        symbols = re.findall(r'\b[A-Z]{1,5}\b', query.upper())
        
        # Detect intent keywords
        intent = "analyze_stock"  # default
        if any(word in query.lower() for word in ["compare", "versus", "vs"]):
            intent = "compare_stocks"
        elif any(word in query.lower() for word in ["technical", "rsi", "macd", "bollinger"]):
            intent = "technical_analysis"
        elif any(word in query.lower() for word in ["fundamental", "earnings", "revenue", "pe"]):
            intent = "fundamental_analysis"
        
        # Determine required tools based on intent
        required_tools = []
        if intent in ["analyze_stock", "compare_stocks"]:
            required_tools = ["stock_analyzer"]
        elif intent == "technical_analysis":
            required_tools = ["technical_indicators"]
        elif intent == "fundamental_analysis":
            required_tools = ["fundamental_analyzer"]
        
        return IntentAnalysis(
            intent=intent,
            entities=StockEntity(symbols=symbols or ["SPY"]),  # Default to SPY
            confidence=0.5,
            reasoning="Extracted using fallback method",
            required_tools=required_tools
        )
    
    async def create_execution_plan_enhanced(self, intent: IntentAnalysis, tools: Dict[str, Any]) -> ExecutionPlan:
        """Create an execution plan using LangChain structured output."""
        tool_descriptions = "\n".join([
            f"- {name}: {tool.get_description() if hasattr(tool, 'get_description') else tool.get('description', 'No description')}"
            for name, tool in tools.items()
        ])
        
        try:
            # Log the prompt for debugging
            logger.debug(f"Plan prompt template: {self.plan_prompt}")
            
            result = await self.plan_chain.ainvoke({
                "intent": intent.intent,
                "entities": intent.entities.dict(),
                "query": intent.reasoning,
                "tool_descriptions": tool_descriptions,
                "format_instructions": self.plan_parser.get_format_instructions()
            })
            
            # Debug logging
            logger.debug(f"Plan chain result type: {type(result)}")
            logger.debug(f"Plan chain result: {result}")
            
            # Check if result is already an ExecutionPlan object
            if isinstance(result, ExecutionPlan):
                return result
            
            # Extract text from result and parse it
            if isinstance(result, dict) and 'text' in result:
                text_output = result['text']
            elif isinstance(result, str):
                text_output = result
            else:
                raise ValueError(f"Unexpected result type: {type(result)}")
            
            # Parse the text output
            return self.plan_parser.parse(text_output)
            
        except Exception as e:
            logger.warning(f"Plan creation failed, using simple plan: {e}")
            # Create simple plan
            return self._create_simple_plan(intent, tools)
    
    def _create_simple_plan(self, intent: IntentAnalysis, tools: Dict[str, Any]) -> ExecutionPlan:
        """Create a simple execution plan as fallback."""
        steps = []
        
        for tool_name in intent.required_tools:
            if tool_name in tools:
                # Map parameters correctly based on tool expectations
                if tool_name == "stock_analyzer":
                    # stock_analyzer expects 'symbol' (singular) not 'symbols'
                    params = {
                        "symbol": intent.entities.symbols[0] if intent.entities.symbols else "SPY",
                        "period": intent.entities.time_period
                    }
                else:
                    params = {
                        "symbols": intent.entities.symbols,
                        "period": intent.entities.time_period
                    }
                
                # Add specific parameters based on tool
                if tool_name == "technical_indicators" and intent.entities.indicators:
                    params["indicators"] = intent.entities.indicators
                
                steps.append(ToolParameters(
                    tool_name=tool_name,
                    parameters=params
                ))
        
        return ExecutionPlan(
            steps=steps,
            description=f"Execute {intent.intent} for {', '.join(intent.entities.symbols)}"
        )
    
    def _transform_parameters_for_tool(self, tool_name: str, params: Dict[str, Any], tool: Any) -> Dict[str, Any]:
        """Transform parameters to match tool expectations."""
        # For stock_analyzer, we know the expected parameters
        if tool_name == "stock_analyzer":
            # Always transform for stock_analyzer regardless of metadata
            transformed = {}
            
            # Handle symbols/symbol parameter
            if 'symbols' in params:
                # Convert list to single value if needed
                if isinstance(params['symbols'], list):
                    transformed['symbol'] = params['symbols'][0] if params['symbols'] else "SPY"
                else:
                    transformed['symbol'] = params['symbols']
            elif 'symbol' in params:
                transformed['symbol'] = params['symbol']
            
            # Handle time_period/period parameter  
            if 'time_period' in params:
                transformed['period'] = params['time_period']
            elif 'period' in params:
                transformed['period'] = params['period']
            else:
                transformed['period'] = '1mo'  # default
                
            logger.debug(f"Transformed parameters for {tool_name}: {params} -> {transformed}")
            return transformed
            
        # For other tools, use the metadata-based approach
        tool_metadata = tool.metadata if hasattr(tool, 'metadata') else {}
        expected_params = tool_metadata.get('parameters', {})
        
        logger.debug(f"Tool metadata for {tool_name}: {tool_metadata}")
        logger.debug(f"Expected parameters: {expected_params}")
        
        # Create parameter mapping based on common transformations
        param_mapping = {
            # Common LLM output -> Tool expected
            'symbols': 'symbol',  # LLM often outputs plural, tools expect singular
            'time_period': 'period',  # More descriptive name to shorter name
            'ticker': 'symbol',  # Alternative naming
            'tickers': 'symbol',  # Alternative plural
            'stock': 'symbol',  # Alternative naming
            'stocks': 'symbol',  # Alternative plural
        }
        
        # Transform parameters
        transformed = {}
        for key, value in params.items():
            # Check if we need to map this parameter
            if key in param_mapping:
                mapped_key = param_mapping[key]
                # Handle list to single value conversion if needed
                if isinstance(value, list) and not mapped_key.endswith('s'):
                    transformed[mapped_key] = value[0] if value else None
                else:
                    transformed[mapped_key] = value
            else:
                # Keep original
                transformed[key] = value
        
        logger.debug(f"Transformed parameters for {tool_name}: {params} -> {transformed}")
        return transformed
    
    async def process_request(self, query: str, conversation_id: str) -> Dict[str, Any]:
        """Process a user request with enhanced LangChain integration."""
        try:
            # 1. Load conversation context
            context = self.context_manager.get_context(conversation_id)
            context['conversation_id'] = conversation_id
            
            # 2. Analyze intent with enhanced parsing
            intent_analysis = await self.analyze_intent_enhanced(query, context)
            
            # Ensure we have an IntentAnalysis object
            if isinstance(intent_analysis, dict):
                intent_analysis = IntentAnalysis(**intent_analysis)
            
            # 3. If tools are needed, load and execute them
            if intent_analysis.required_tools:
                tools = await self.tool_registry.load_tools_from_registry(intent_analysis.required_tools)
                
                # 4. Create execution plan with structured output
                plan = await self.create_execution_plan_enhanced(intent_analysis, tools)
                
                # 5. Execute the plan
                results = await self.execute_plan(plan, tools)
                
                # 6. Update context
                self._update_context_from_execution(conversation_id, intent_analysis, results)
                
                # 7. Format response
                response = await self.format_response(results, intent_analysis)
            else:
                # No tools needed - return a direct response
                response = self._get_no_tools_response(intent_analysis)
                results = {"no_tools_used": True}
            
            return {
                "response": response,
                "metadata": {
                    "intent": intent_analysis.intent,
                    "confidence": intent_analysis.confidence,
                    "tools_used": intent_analysis.required_tools,
                    "execution_time": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "error": True
            }
    
    async def execute_plan(self, plan: ExecutionPlan, tools: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plan steps sequentially."""
        results = {
            "steps_executed": [],
            "final_results": {}
        }
        
        for step in plan.steps:
            try:
                tool = tools.get(step.tool_name)
                if tool:
                    # Transform parameters based on tool requirements
                    logger.debug(f"Original parameters for {step.tool_name}: {step.parameters}")
                    transformed_params = self._transform_parameters_for_tool(
                        step.tool_name, 
                        step.parameters,
                        tool
                    )
                    logger.debug(f"Transformed parameters for {step.tool_name}: {transformed_params}")
                    
                    # Handle both RemoteTool objects and dict-based tools
                    if hasattr(tool, 'execute'):
                        step_result = await tool.execute(**transformed_params)
                    elif isinstance(tool, dict) and callable(tool.get('execute')):
                        step_result = await tool['execute'](**transformed_params)
                    else:
                        raise ValueError(f"Tool {step.tool_name} has no execute method")
                    results["steps_executed"].append({
                        "tool": step.tool_name,
                        "result": step_result
                    })
                    results["final_results"][step.tool_name] = step_result
            except Exception as e:
                logger.error(f"Error executing {step.tool_name}: {e}")
                results["steps_executed"].append({
                    "tool": step.tool_name,
                    "error": str(e)
                })
        
        return results
    
    def _update_context_from_execution(self, conversation_id: str, intent: IntentAnalysis, results: Dict[str, Any]):
        """Update context manager with execution details."""
        self.context_manager.add_message(conversation_id, {
            "type": "execution",
            "intent": intent.intent,
            "entities": intent.entities.dict(),
            "tools_used": intent.required_tools,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update entity tracking
        for symbol in intent.entities.symbols:
            self.context_manager.track_entity(conversation_id, "stock", symbol)
    
    async def format_response(self, results: Dict[str, Any], intent: IntentAnalysis) -> str:
        """Format the execution results into a user-friendly response."""
        if results.get("no_tools_used"):
            return results.get("response", "I can help you with stock analysis.")
        
        # Build response from results
        response_parts = []
        
        for step in results.get("steps_executed", []):
            if "error" in step:
                response_parts.append(f"Error with {step['tool']}: {step['error']}")
            else:
                # Format based on tool type
                tool_name = step["tool"]
                result = step["result"]
                
                if tool_name == "stock_analyzer":
                    response_parts.append(self._format_stock_analysis(result))
                elif tool_name == "technical_indicators":
                    response_parts.append(self._format_technical_analysis(result))
                elif tool_name == "fundamental_analyzer":
                    response_parts.append(self._format_fundamental_analysis(result))
        
        return "\n\n".join(response_parts)
    
    def _get_no_tools_response(self, intent: IntentAnalysis) -> str:
        """Generate response when no tools are needed."""
        responses = {
            "greeting": "Hello! I can help you analyze stocks, view technical indicators, and check company fundamentals.",
            "help": "I can: analyze individual stocks, compare multiple stocks, show technical indicators, and provide fundamental analysis.",
            "unknown": "I can help you with stock analysis. Try asking about specific stocks or indicators."
        }
        
        return responses.get(intent.intent, responses["unknown"])
    
    def _format_stock_analysis(self, data: Dict[str, Any]) -> str:
        """Format stock analysis results."""
        return f"Stock Analysis: {json.dumps(data, indent=2)}"
    
    def _format_technical_analysis(self, data: Dict[str, Any]) -> str:
        """Format technical analysis results."""
        return f"Technical Indicators: {json.dumps(data, indent=2)}"
    
    def _format_fundamental_analysis(self, data: Dict[str, Any]) -> str:
        """Format fundamental analysis results."""
        return f"Fundamental Analysis: {json.dumps(data, indent=2)}"
    
    async def process_request_stream(self, query: str, conversation_id: str):
        """Process request with streaming support."""
        try:
            # For now, process the full request and yield it in chunks
            result = await self.process_request(query, conversation_id)
            
            # Yield the response in chunks
            response_text = result.get("response", "")
            chunk_size = 50  # Characters per chunk
            
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield {
                    "type": "content",
                    "content": chunk
                }
                await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            # Yield metadata at the end
            if "metadata" in result:
                yield {
                    "type": "metadata",
                    "metadata": result["metadata"]
                }
                
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }