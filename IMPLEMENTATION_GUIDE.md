# Genesis Agent - Tool Registry Implementation Guide

## Overview

This guide shows how to implement the agent-based tool registry system that replaces hardcoded intent matching with intelligent, context-aware tool selection.

## Architecture Changes

### Before (Hardcoded Intent Matching)
```
User Query → Intent Analysis → Hardcoded Mapping → Tool Selection → Execution
```

### After (Agent-Based Selection)
```
User Query → Agent (with Tool Registry) → Intelligent Selection → Execution
                    ↑
              Context Manager
```

## Key Components

### 1. Tool Registry (`tools/registry.py`)
- Central definition of all available tools
- Rich metadata including `when_to_use` and `examples`
- No code changes needed to add new tools

### 2. Enhanced Genesis Agent (`agent/enhanced_genesis_agent.py`)
- Replaces hardcoded intent matching
- Uses system prompt with tool registry
- Makes intelligent decisions based on query and context

### 3. Enhanced Context Manager (`agent/enhanced_context_manager.py`)
- Tracks entities, tools, and conversation flow
- Provides context for ambiguous queries
- Suggests next analysis steps

### 4. Enhanced Dynamic Loader (`tools/registry/enhanced_dynamic_loader.py`)
- Bridges tool registry with MCP infrastructure
- Maps registry keys to actual tool implementations
- Supports context-aware tool search

## Migration Steps

### Step 1: Update Your Imports

```python
# Old imports
from agent.genesis_agent import GenesisAgent
from agent.context_manager import ContextManager
from tools.registry.dynamic_loader import DynamicToolRegistry

# New imports
from agent.enhanced_genesis_agent import EnhancedGenesisAgent
from agent.enhanced_context_manager import EnhancedContextManager
from tools.registry.enhanced_dynamic_loader import EnhancedDynamicToolRegistry
```

### Step 2: Update API Endpoints

```python
# In ui/api/main.py

# Old initialization
agent = GenesisAgent()

# New initialization
agent = EnhancedGenesisAgent()
context_manager = EnhancedContextManager()
```

### Step 3: Update Tool Loading

```python
# The agent now handles tool selection internally
# No need to manually determine tools based on intent
```

### Step 4: Add New Tools

To add a new tool, simply update the registry:

```python
# In tools/registry.py
TOOL_REGISTRY["new_tool_name"] = {
    "id": "service.actual_tool_id",
    "description": "What this tool does",
    "when_to_use": "Specific conditions when to use this tool",
    "examples": [
        "Example query 1",
        "Example query 2"
    ],
    "requires": ["required_param"],
    "optional_params": ["optional_param"],
    "category": "tool_category"
}
```

## Usage Examples

### Basic Query
```python
# User: "What's Apple's stock price?"
result = await agent.process_request("What's Apple's stock price?", "conv_123")
# Agent automatically selects stock_analyzer tool
```

### Ambiguous Query with Context
```python
# First query
await agent.process_request("Analyze AAPL", "conv_123")

# Follow-up (ambiguous)
await agent.process_request("What about the fundamentals?", "conv_123")
# Agent uses context to know user means AAPL fundamentals
```

### Complex Multi-Tool Query
```python
# User: "Compare Apple and Microsoft technical indicators"
result = await agent.process_request(
    "Compare Apple and Microsoft technical indicators", 
    "conv_123"
)
# Agent selects: technical_indicators (2x) + stock_comparer
```

## Testing Your Implementation

Run the test suite:

```bash
pytest tests/test_tool_selection.py -v
```

Key test scenarios:
1. Simple direct queries
2. No tools needed (capability questions)
3. Ambiguous queries with context
4. Time modifiers
5. Multi-tool coordination
6. No default tool behavior

## Best Practices

### 1. Tool Descriptions
- Be specific in `when_to_use` descriptions
- Provide clear, realistic examples
- Use consistent terminology

### 2. Context Management
- Always update context after tool execution
- Track entities and tools used
- Clean old cache periodically

### 3. Error Handling
- Handle cases where no tools match
- Provide helpful responses when tools aren't appropriate
- Log tool selection reasoning for debugging

### 4. Performance
- Tools are loaded on-demand
- Context is cached efficiently
- Registry lookups are O(1)

## Monitoring

Add logging to track tool selection:

```python
logger.info(f"Query: {query}")
logger.info(f"Tools selected: {analysis['tools_to_use']}")
logger.info(f"Reasoning: {analysis['reasoning']}")
```

## Scaling to 100+ Tools

The system is designed to scale:

1. **Organize by Category**: Group related tools
2. **Use Subcategories**: For very large sets
3. **Dynamic Loading**: Tools loaded only when needed
4. **Efficient Search**: Registry supports fast lookups

Example with many tools:
```python
TOOL_REGISTRY = {
    "market_data": {
        "stock_price": {...},
        "options_chain": {...},
        "futures_data": {...},
        # ... 20+ market data tools
    },
    "analysis": {
        "fundamental": {...},
        "technical": {...},
        "quantitative": {...},
        # ... 30+ analysis tools
    },
    "research": {
        "news_search": {...},
        "sec_filings": {...},
        "analyst_reports": {...},
        # ... 20+ research tools
    }
}
```

## Troubleshooting

### Tools Not Being Selected
1. Check tool registry `when_to_use` descriptions
2. Verify examples match user queries
3. Check context is being updated correctly

### Wrong Tools Selected
1. Make descriptions more specific
2. Add disambiguating examples
3. Check for overlapping tool purposes

### Performance Issues
1. Ensure tools are cached properly
2. Check MCP connection pooling
3. Monitor context size (auto-trimmed to 50 messages)

## Future Enhancements

1. **Semantic Search**: Use embeddings for better tool matching
2. **Tool Composition**: Automatic tool chaining for complex tasks
3. **Learning**: Track successful tool selections to improve over time
4. **Tool Versioning**: Support multiple versions of tools

## Conclusion

The agent-based tool registry provides a flexible, scalable foundation for Genesis. By removing hardcoded logic and letting the agent make intelligent decisions, the system can grow to hundreds of tools while maintaining accuracy and performance.