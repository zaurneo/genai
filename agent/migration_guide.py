"""
Migration Guide: From Hardcoded Intent Matching to Agent-Based Tool Selection

This module provides utilities and examples for migrating from the old
hardcoded intent system to the new agent-based tool selection.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class AgentMigrationHelper:
    """Helper class to facilitate migration to the enhanced agent."""
    
    @staticmethod
    def compare_approaches(query: str) -> Dict[str, Any]:
        """Show the difference between old and new approaches."""
        
        # Old approach - hardcoded intent matching
        old_approach = {
            "method": "hardcoded_intent_matching",
            "code_example": """
# OLD APPROACH - DO NOT USE
async def determine_tools(self, intent: Dict[str, Any]) -> List[str]:
    intent_to_tools = {
        "analyze_stock": ["stock_data.get_price", "stock_data.get_fundamentals"],
        "compare_stocks": ["stock_data.get_price", "technical.compare_performance"],
        # ... more hardcoded mappings
    }
    return intent_to_tools.get(intent["intent"], ["stock_data.get_price"])
            """,
            "problems": [
                "Rigid - adding new tools requires code changes",
                "No context awareness",
                "Defaults to arbitrary tool",
                "Can't handle ambiguous queries",
                "Doesn't scale to many tools"
            ]
        }
        
        # New approach - agent-based selection
        new_approach = {
            "method": "agent_based_selection",
            "code_example": """
# NEW APPROACH - RECOMMENDED
async def analyze_with_tools(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    # Agent sees all available tools in registry
    # Makes intelligent decisions based on query and context
    # No hardcoded mappings needed
    prompt = self.get_system_prompt(context)  # Includes tool registry
    return await self.llm_adapter.complete(prompt + query)
            """,
            "benefits": [
                "Flexible - add tools by updating registry only",
                "Context-aware decisions",
                "No arbitrary defaults",
                "Handles ambiguous queries intelligently",
                "Scales to hundreds of tools"
            ]
        }
        
        return {
            "query": query,
            "old_approach": old_approach,
            "new_approach": new_approach
        }
    
    @staticmethod
    def migrate_intent_mappings() -> Dict[str, Any]:
        """Convert old intent mappings to tool registry entries."""
        
        # Example of converting old mappings
        old_mappings = {
            "analyze_stock": ["stock_data.get_price", "stock_data.get_fundamentals"],
            "technical_analysis": ["technical.calculate_indicators", "technical.analyze_patterns"]
        }
        
        # Convert to registry format
        migrated_entries = {}
        
        migrated_entries["example_conversion"] = {
            "from": "hardcoded intent 'analyze_stock'",
            "to": """
TOOL_REGISTRY["stock_analyzer"] = {
    "id": "stock_data.get_price",
    "description": "Analyzes stock prices and historical data",
    "when_to_use": "User asks about stock prices, performance, or history",
    "examples": ["What's AAPL price?", "How has TSLA performed?"],
    "requires": ["ticker_symbol"]
}
            """
        }
        
        return migrated_entries
    
    @staticmethod
    def test_migration_scenarios() -> List[Dict[str, Any]]:
        """Test scenarios to verify the migration works correctly."""
        
        test_cases = [
            {
                "scenario": "Simple price query",
                "query": "What's Apple's stock price?",
                "old_behavior": "Maps to 'analyze_stock' intent → uses hardcoded tools",
                "new_behavior": "Agent sees query matches stock_analyzer tool → uses it directly",
                "expected_tools": ["stock_analyzer"]
            },
            {
                "scenario": "Ambiguous follow-up",
                "query": "What about Microsoft?",
                "old_behavior": "Fails or defaults to generic tool",
                "new_behavior": "Agent checks context, sees previous was price query → uses stock_analyzer for MSFT",
                "expected_tools": ["stock_analyzer"],
                "requires_context": True
            },
            {
                "scenario": "Capability question",
                "query": "What can you do?",
                "old_behavior": "Might incorrectly trigger a tool",
                "new_behavior": "Agent recognizes no tool needed → explains capabilities",
                "expected_tools": []
            },
            {
                "scenario": "Complex multi-tool request",
                "query": "Compare Apple and Microsoft fundamentals and show me their technical indicators",
                "old_behavior": "Might miss some tools or use wrong combination",
                "new_behavior": "Agent intelligently selects: fundamental_analyzer (x2), technical_indicators (x2), stock_comparer",
                "expected_tools": ["fundamental_analyzer", "technical_indicators", "stock_comparer"]
            }
        ]
        
        return test_cases

# Migration steps for existing codebase
MIGRATION_STEPS = """
STEP-BY-STEP MIGRATION GUIDE:

1. **Create Tool Registry** (DONE)
   - Define all tools in registry.py
   - Include when_to_use, examples, and requirements

2. **Update Agent Class** (DONE)
   - Replace analyze_intent() and determine_tools() with analyze_with_tools()
   - Update system prompt to include tool registry
   - Remove hardcoded intent mappings

3. **Enhance Context Management**
   - Track last_entity, last_tool, recent_entities
   - Use context for ambiguous queries

4. **Update Dynamic Loader**
   - Ensure it can work with tool registry format
   - Map registry entries to actual tool IDs

5. **Test Thoroughly**
   - Run test scenarios
   - Verify no tools are used by default
   - Check ambiguous query handling

6. **Update API Layer**
   - Switch to enhanced agent
   - Ensure streaming still works
   - Update response format if needed

7. **Monitor and Iterate**
   - Log tool selection reasoning
   - Gather feedback on accuracy
   - Refine tool descriptions as needed
"""

def demonstrate_context_handling():
    """Show how context improves tool selection."""
    
    example_conversation = [
        {
            "user": "Analyze Apple stock",
            "agent_reasoning": "Clear request for Apple (AAPL) analysis",
            "tools_selected": ["stock_analyzer", "fundamental_analyzer"],
            "context_update": {"last_entity": "AAPL", "last_tool": "stock_analyzer"}
        },
        {
            "user": "What about the technical indicators?",
            "agent_reasoning": "Context shows last_entity=AAPL, user asking about technical analysis",
            "tools_selected": ["technical_indicators with symbol=AAPL"],
            "context_update": {"last_tool": "technical_indicators"}
        },
        {
            "user": "Compare it with Microsoft",
            "agent_reasoning": "Context has AAPL, user wants comparison with MSFT",
            "tools_selected": ["stock_comparer with symbols=[AAPL, MSFT]"],
            "context_update": {"recent_entities": ["AAPL", "MSFT"], "last_tool": "stock_comparer"}
        }
    ]
    
    return example_conversation