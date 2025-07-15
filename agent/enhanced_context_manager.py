from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta
import redis
import hashlib
import logging
from collections import deque

logger = logging.getLogger(__name__)

class EnhancedContextManager:
    """Enhanced context manager that tracks entities, tools, and conversation flow."""
    
    def __init__(self, redis_url: str = None):
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        else:
            # Use in-memory storage for development
            self.memory_store = {}
    
    def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Retrieve enhanced context for a conversation."""
        context = None
        
        if hasattr(self, 'redis_client'):
            data = self.redis_client.get(f"context:{conversation_id}")
            if data:
                context = json.loads(data)
        else:
            context = self.memory_store.get(conversation_id)
        
        # Return context if found, otherwise return default enhanced context
        if context:
            return context
        
        # Return enhanced default context
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "entities": {
                "last_entity": None,
                "recent_entities": deque(maxlen=10),  # Will be converted to list for storage
                "entity_history": {}  # Track what was done with each entity
            },
            "tools": {
                "last_tool": None,
                "tool_sequence": deque(maxlen=20),  # Will be converted to list for storage
                "tool_results": {}  # Cache recent tool results
            },
            "conversation": {
                "topic": None,
                "intent_flow": [],  # Track how conversation intent changes
                "time_context": None,  # Track time-related queries
                "comparison_context": None  # Track comparison queries
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "interaction_count": 0
            }
        }
    
    def update(self, conversation_id: str, query: str, updates: Dict[str, Any]):
        """Update conversation context with rich information."""
        context = self.get_context(conversation_id)
        
        # Convert deques to lists for storage
        if isinstance(context.get('entities', {}).get('recent_entities'), deque):
            context['entities']['recent_entities'] = list(context['entities']['recent_entities'])
        if isinstance(context.get('tools', {}).get('tool_sequence'), deque):
            context['tools']['tool_sequence'] = list(context['tools']['tool_sequence'])
        
        # Update entities
        if 'last_entity' in updates:
            context['entities']['last_entity'] = updates['last_entity']
            
            # Convert back to deque for operations
            recent = deque(context['entities']['recent_entities'], maxlen=10)
            if updates['last_entity'] not in recent:
                recent.append(updates['last_entity'])
            context['entities']['recent_entities'] = list(recent)
            
            # Track what was done with this entity
            if 'last_tool' in updates:
                if updates['last_entity'] not in context['entities']['entity_history']:
                    context['entities']['entity_history'][updates['last_entity']] = []
                context['entities']['entity_history'][updates['last_entity']].append({
                    "tool": updates['last_tool'],
                    "timestamp": datetime.now().isoformat()
                })
        
        # Update tools
        if 'last_tool' in updates:
            context['tools']['last_tool'] = updates['last_tool']
            
            # Convert back to deque for operations
            tool_seq = deque(context['tools']['tool_sequence'], maxlen=20)
            tool_seq.append(updates['last_tool'])
            context['tools']['tool_sequence'] = list(tool_seq)
        
        # Update conversation flow
        if 'topic' in updates:
            context['conversation']['topic'] = updates['topic']
        
        if 'time_context' in updates:
            context['conversation']['time_context'] = updates['time_context']
        
        if 'comparison_context' in updates:
            context['conversation']['comparison_context'] = updates['comparison_context']
        
        # Cache tool results if provided
        if 'tool_results' in updates:
            for tool_key, result in updates['tool_results'].items():
                # Cache with timestamp
                context['tools']['tool_results'][tool_key] = {
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Add message to history
        context["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "updates": updates,
            "hash": self._hash_message(query)
        })
        
        # Keep only last 50 messages
        if len(context["messages"]) > 50:
            context["messages"] = context["messages"][-50:]
        
        # Update metadata
        context["metadata"]["last_updated"] = datetime.now().isoformat()
        context["metadata"]["interaction_count"] += 1
        
        # Clean old cached results (older than 10 minutes)
        self._clean_old_cache(context['tools']['tool_results'])
        
        # Save context
        if hasattr(self, 'redis_client'):
            self.redis_client.setex(
                f"context:{conversation_id}",
                3600 * 24,  # 24 hour TTL
                json.dumps(context)
            )
        else:
            self.memory_store[conversation_id] = context
    
    def get_contextual_hints(self, conversation_id: str, query: str) -> Dict[str, Any]:
        """Get hints for tool selection based on context and query."""
        context = self.get_context(conversation_id)
        hints = {
            "suggested_entity": None,
            "suggested_tools": [],
            "time_modifier": None,
            "comparison_hint": None
        }
        
        query_lower = query.lower()
        
        # Check for ambiguous references
        if any(phrase in query_lower for phrase in ["what about", "how about", "and for", "same for"]):
            # Suggest using last entity
            hints["suggested_entity"] = context['entities']['last_entity']
            
            # Suggest similar tool as last used
            if context['tools']['last_tool']:
                hints["suggested_tools"].append(context['tools']['last_tool'])
        
        # Check for time modifiers
        time_phrases = {
            "last year": {"period": "1y"},
            "last month": {"period": "1mo"},
            "last week": {"period": "1wk"},
            "yesterday": {"period": "1d"},
            "ytd": {"period": "ytd"},
            "year to date": {"period": "ytd"}
        }
        
        for phrase, time_info in time_phrases.items():
            if phrase in query_lower:
                hints["time_modifier"] = time_info
                break
        
        # Check for comparison references
        if any(word in query_lower for word in ["compare", "versus", "vs", "against", "with"]):
            # Get recent entities for comparison
            recent = list(context['entities']['recent_entities'])
            if len(recent) >= 2:
                hints["comparison_hint"] = {
                    "entities": recent[-2:],  # Last two entities
                    "suggested_tool": "stock_comparer"
                }
        
        # Check for follow-up patterns
        if "why" in query_lower and context['entities']['last_entity']:
            # User asking why something happened - might need news tool in future
            hints["suggested_tools"].append("news_analyzer")  # Future tool
        
        return hints
    
    def get_entity_context(self, conversation_id: str, entity: str) -> Dict[str, Any]:
        """Get all context related to a specific entity."""
        context = self.get_context(conversation_id)
        
        entity_context = {
            "entity": entity,
            "last_analyzed": None,
            "tools_used": [],
            "cached_results": {}
        }
        
        # Get history for this entity
        if entity in context['entities']['entity_history']:
            history = context['entities']['entity_history'][entity]
            if history:
                entity_context["last_analyzed"] = history[-1]["timestamp"]
                entity_context["tools_used"] = [h["tool"] for h in history]
        
        # Get cached results for this entity
        for key, value in context['tools']['tool_results'].items():
            if entity in key:
                entity_context["cached_results"][key] = value
        
        return entity_context
    
    def suggest_next_analysis(self, conversation_id: str) -> List[Dict[str, str]]:
        """Suggest next analysis steps based on conversation flow."""
        context = self.get_context(conversation_id)
        suggestions = []
        
        last_tool = context['tools']['last_tool']
        last_entity = context['entities']['last_entity']
        
        if not last_entity:
            return suggestions
        
        # Suggest complementary analyses
        tool_flow = {
            "stock_analyzer": ["fundamental_analyzer", "technical_indicators"],
            "fundamental_analyzer": ["financial_statements", "stock_comparer"],
            "technical_indicators": ["pattern_analyzer", "stock_analyzer"],
            "pattern_analyzer": ["technical_indicators", "stock_comparer"]
        }
        
        if last_tool in tool_flow:
            for suggested_tool in tool_flow[last_tool]:
                # Only suggest if not recently used
                recent_tools = context['tools']['tool_sequence'][-3:] if len(context['tools']['tool_sequence']) >= 3 else context['tools']['tool_sequence']
                if suggested_tool not in recent_tools:
                    suggestions.append({
                        "tool": suggested_tool,
                        "reason": f"Natural follow-up to {last_tool}",
                        "entity": last_entity
                    })
        
        return suggestions[:2]  # Limit suggestions
    
    def _clean_old_cache(self, cache: Dict[str, Any], max_age_minutes: int = 10):
        """Remove cached results older than max_age_minutes."""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, value in cache.items():
            if 'timestamp' in value:
                timestamp = datetime.fromisoformat(value['timestamp'])
                if current_time - timestamp > timedelta(minutes=max_age_minutes):
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del cache[key]
    
    def _hash_message(self, message: str) -> str:
        """Create a hash of a message for deduplication."""
        return hashlib.sha256(message.encode()).hexdigest()[:16]
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation for agent context."""
        context = self.get_context(conversation_id)
        
        # Ensure we're working with lists, not deques
        recent_entities = list(context['entities']['recent_entities']) if isinstance(context['entities']['recent_entities'], deque) else context['entities']['recent_entities']
        tool_sequence = list(context['tools']['tool_sequence']) if isinstance(context['tools']['tool_sequence'], deque) else context['tools']['tool_sequence']
        
        return {
            "last_entity": context['entities']['last_entity'],
            "recent_entities": recent_entities[-5:] if recent_entities else [],
            "last_tool": context['tools']['last_tool'],
            "recent_tools": tool_sequence[-5:] if tool_sequence else [],
            "topic": context['conversation']['topic'],
            "interaction_count": context['metadata']['interaction_count']
        }
    
    def add_message(self, conversation_id: str, message: Dict[str, Any]):
        """Add a message to the conversation history."""
        context = self.get_context(conversation_id)
        
        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()
        
        # Add to messages
        context['messages'].append(message)
        
        # Update metadata
        context['metadata']['last_updated'] = datetime.now().isoformat()
        context['metadata']['interaction_count'] += 1
        
        # Save context
        self.update(conversation_id, "", context)
    
    def track_entity(self, conversation_id: str, entity_type: str, entity_value: str):
        """Track an entity in the conversation."""
        context = self.get_context(conversation_id)
        
        # Update last entity
        context['entities']['last_entity'] = entity_value
        
        # Add to recent entities (handle deque)
        if isinstance(context['entities']['recent_entities'], deque):
            context['entities']['recent_entities'].append(entity_value)
        else:
            context['entities']['recent_entities'] = deque(context['entities']['recent_entities'], maxlen=10)
            context['entities']['recent_entities'].append(entity_value)
        
        # Track in entity history
        if entity_value not in context['entities']['entity_history']:
            context['entities']['entity_history'][entity_value] = {
                'type': entity_type,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'count': 0
            }
        
        context['entities']['entity_history'][entity_value]['count'] += 1
        context['entities']['entity_history'][entity_value]['last_seen'] = datetime.now().isoformat()
        
        # Save context
        self.update(conversation_id, "", context)