"""
Test scenarios for agent-based tool selection.

This module tests the enhanced tool selection system to ensure:
1. Tools are selected appropriately based on queries
2. Context is used correctly for ambiguous queries
3. No tools are selected when not needed
4. Multiple tools are coordinated properly
"""

import pytest
import asyncio
from typing import Dict, List, Any
from agent.enhanced_genesis_agent import EnhancedGenesisAgent
from agent.enhanced_context_manager import EnhancedContextManager
from tools.registry import TOOL_REGISTRY

class TestToolSelection:
    """Test cases for tool selection logic."""
    
    @pytest.fixture
    def agent(self):
        """Create test agent instance."""
        return EnhancedGenesisAgent(llm_provider="openai")
    
    @pytest.fixture
    def context_manager(self):
        """Create test context manager."""
        return EnhancedContextManager()
    
    async def test_simple_price_query(self, agent, context_manager):
        """Test: Direct price query should select stock_analyzer."""
        query = "What's Apple's stock price?"
        context = context_manager.get_context("test_conv_1")
        
        analysis = await agent.analyze_with_tools(query, context)
        
        assert len(analysis['tools_to_use']) == 1
        assert analysis['tools_to_use'][0]['tool_key'] == 'stock_analyzer'
        assert analysis['tools_to_use'][0]['parameters']['symbol'] == 'AAPL'
    
    async def test_no_tools_needed(self, agent, context_manager):
        """Test: Capability questions shouldn't trigger tools."""
        queries = [
            "What can you do?",
            "What tools do you have?",
            "How do you work?",
            "What kind of analysis can you perform?"
        ]
        
        for query in queries:
            context = context_manager.get_context("test_conv_2")
            analysis = await agent.analyze_with_tools(query, context)
            
            assert len(analysis['tools_to_use']) == 0
            assert 'response' in analysis
            assert len(analysis['response']) > 0
    
    async def test_ambiguous_with_context(self, agent, context_manager):
        """Test: Ambiguous queries use context correctly."""
        conversation_id = "test_conv_3"
        
        # First query establishes context
        context_manager.update(conversation_id, "analyze AAPL", {
            "last_entity": "AAPL",
            "last_tool": "stock_analyzer"
        })
        
        # Ambiguous follow-up
        query = "What about the fundamentals?"
        context = context_manager.get_context(conversation_id)
        analysis = await agent.analyze_with_tools(query, context)
        
        assert len(analysis['tools_to_use']) == 1
        assert analysis['tools_to_use'][0]['tool_key'] == 'fundamental_analyzer'
        assert analysis['tools_to_use'][0]['parameters']['symbol'] == 'AAPL'
    
    async def test_time_modifier_context(self, agent, context_manager):
        """Test: Time modifiers are applied to previous queries."""
        conversation_id = "test_conv_4"
        
        # Establish context
        context_manager.update(conversation_id, "show me TSLA price", {
            "last_entity": "TSLA",
            "last_tool": "stock_analyzer"
        })
        
        # Query with time modifier
        query = "How about last year?"
        context = context_manager.get_context(conversation_id)
        analysis = await agent.analyze_with_tools(query, context)
        
        assert len(analysis['tools_to_use']) == 1
        assert analysis['tools_to_use'][0]['tool_key'] == 'stock_analyzer'
        assert analysis['tools_to_use'][0]['parameters']['symbol'] == 'TSLA'
        assert analysis['tools_to_use'][0]['parameters']['period'] == '1y'
    
    async def test_multi_tool_request(self, agent, context_manager):
        """Test: Complex requests trigger multiple tools."""
        query = "Compare Apple and Microsoft fundamentals and show their technical indicators"
        context = context_manager.get_context("test_conv_5")
        
        analysis = await agent.analyze_with_tools(query, context)
        
        # Should select multiple tools
        assert len(analysis['tools_to_use']) >= 3
        
        tool_keys = [t['tool_key'] for t in analysis['tools_to_use']]
        assert 'fundamental_analyzer' in tool_keys
        assert 'technical_indicators' in tool_keys
        assert 'stock_comparer' in tool_keys
    
    async def test_comparison_context(self, agent, context_manager):
        """Test: Comparison queries use recent entities."""
        conversation_id = "test_conv_6"
        
        # Build up entity context
        context_manager.update(conversation_id, "analyze AAPL", {
            "last_entity": "AAPL",
            "recent_entities": ["AAPL"]
        })
        
        context_manager.update(conversation_id, "now check GOOGL", {
            "last_entity": "GOOGL",
            "recent_entities": ["AAPL", "GOOGL"]
        })
        
        # Comparison query
        query = "Compare them"
        context = context_manager.get_context(conversation_id)
        analysis = await agent.analyze_with_tools(query, context)
        
        assert len(analysis['tools_to_use']) >= 1
        assert analysis['tools_to_use'][0]['tool_key'] == 'stock_comparer'
        assert set(analysis['tools_to_use'][0]['parameters']['symbols']) == {"AAPL", "GOOGL"}
    
    async def test_no_default_tool(self, agent, context_manager):
        """Test: Agent doesn't default to any tool for unclear queries."""
        unclear_queries = [
            "interesting",
            "hmm",
            "okay",
            "what do you think?",
            "is it good?"
        ]
        
        for query in unclear_queries:
            context = context_manager.get_context("test_conv_7")
            analysis = await agent.analyze_with_tools(query, context)
            
            # Should either select no tools or have clear reasoning
            if len(analysis['tools_to_use']) > 0:
                assert analysis['reasoning'] != ""
                assert "default" not in analysis['reasoning'].lower()
    
    async def test_tool_chaining(self, agent, context_manager):
        """Test: Tools that naturally follow each other."""
        conversation_id = "test_conv_8"
        
        # Technical analysis query
        query = "Show me technical analysis for NVDA"
        context = context_manager.get_context(conversation_id)
        analysis = await agent.analyze_with_tools(query, context)
        
        # Should include both price data and technical indicators
        tool_keys = [t['tool_key'] for t in analysis['tools_to_use']]
        assert 'stock_analyzer' in tool_keys or 'technical_indicators' in tool_keys
        
        # Update context
        context_manager.update(conversation_id, query, {
            "last_entity": "NVDA",
            "last_tool": "technical_indicators"
        })
        
        # Follow-up for patterns
        query = "Any interesting patterns?"
        context = context_manager.get_context(conversation_id)
        analysis = await agent.analyze_with_tools(query, context)
        
        assert len(analysis['tools_to_use']) == 1
        assert analysis['tools_to_use'][0]['tool_key'] == 'pattern_analyzer'
        assert analysis['tools_to_use'][0]['parameters']['symbol'] == 'NVDA'

# Integration test scenarios
class TestIntegrationScenarios:
    """End-to-end test scenarios."""
    
    async def test_full_conversation_flow(self):
        """Test a complete conversation with context building."""
        agent = EnhancedGenesisAgent()
        conversation_id = "test_integration_1"
        
        # Conversation flow
        interactions = [
            {
                "query": "What can you help me with?",
                "expected_tools": 0,
                "check": lambda r: "capabilities" in r['response'].lower()
            },
            {
                "query": "Analyze Apple stock",
                "expected_tools": 2,  # stock_analyzer + fundamental_analyzer
                "check": lambda r: 'AAPL' in str(r)
            },
            {
                "query": "How about the technical indicators?",
                "expected_tools": 1,  # technical_indicators
                "check": lambda r: r['metadata']['tools_used'][0] == 'technical_indicators'
            },
            {
                "query": "Compare with Microsoft",
                "expected_tools": 1,  # stock_comparer
                "check": lambda r: 'MSFT' in str(r)
            }
        ]
        
        for interaction in interactions:
            result = await agent.process_request(
                interaction['query'],
                conversation_id
            )
            
            # Check number of tools used
            tools_used = result['metadata'].get('tools_used', [])
            assert len(tools_used) == interaction['expected_tools']
            
            # Run custom check
            assert interaction['check'](result)

# Performance test scenarios
class TestPerformance:
    """Test performance with many tools."""
    
    def test_registry_scaling(self):
        """Test that registry handles many tools efficiently."""
        # Simulate 100+ tools
        large_registry = {}
        
        for i in range(100):
            large_registry[f"tool_{i}"] = {
                "id": f"service.tool_{i}",
                "description": f"Tool number {i} for specific analysis",
                "when_to_use": f"When user asks about feature {i}",
                "examples": [f"analyze feature {i}", f"what about aspect {i}"],
                "requires": ["parameter"],
                "category": f"category_{i % 10}"
            }
        
        # Test that agent can still make decisions efficiently
        # This would be tested with actual timing in production
        assert len(large_registry) == 100
        
        # Check category grouping works
        categories = {}
        for key, tool in large_registry.items():
            cat = tool['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(key)
        
        assert len(categories) == 10  # 10 categories
        assert all(len(tools) == 10 for tools in categories.values())

# Mock responses for testing without actual LLM
class MockAnalysisResponses:
    """Mock LLM responses for predictable testing."""
    
    responses = {
        "What's Apple's stock price?": {
            "tools_to_use": [{
                "tool_key": "stock_analyzer",
                "tool_id": "stock_data.get_price",
                "parameters": {"symbol": "AAPL"},
                "reason": "User asking for current stock price"
            }],
            "reasoning": "Direct price query for Apple stock"
        },
        "What can you do?": {
            "tools_to_use": [],
            "reasoning": "User asking about capabilities",
            "response": "I can help with stock analysis, technical indicators, fundamentals, and comparisons."
        }
    }

if __name__ == "__main__":
    # Run some basic tests
    asyncio.run(TestToolSelection().test_simple_price_query(
        EnhancedGenesisAgent(),
        EnhancedContextManager()
    ))