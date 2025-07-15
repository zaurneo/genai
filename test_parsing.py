#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.append('/app' if os.path.exists('/app') else '.')

from agent.enhanced_genesis_agent import EnhancedGenesisAgent

async def test_parsing():
    """Test the parsing functionality"""
    agent = EnhancedGenesisAgent()
    
    # Test query
    query = "What's the price of AAPL?"
    conversation_id = "test123"
    
    print("Testing intent analysis...")
    
    # Get context
    context = agent.context_manager.get_context(conversation_id)
    
    try:
        # Test intent analysis
        intent = await agent.analyze_intent_enhanced(query, context)
        print(f"Intent analysis result type: {type(intent)}")
        print(f"Intent analysis result: {intent}")
        
        if hasattr(intent, 'intent'):
            print(f"Intent: {intent.intent}")
            print(f"Symbols: {intent.entities.symbols}")
            print(f"Required tools: {intent.required_tools}")
    except Exception as e:
        print(f"Error during intent analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parsing())