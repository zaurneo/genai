from typing import Dict, Any, List
import json
from datetime import datetime
import redis
import hashlib
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    """Manages conversation context and history."""
    
    def __init__(self, redis_url: str = None):
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        else:
            # Use in-memory storage for development
            self.memory_store = {}
    
    def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Retrieve context for a conversation."""
        context = None
        
        if hasattr(self, 'redis_client'):
            data = self.redis_client.get(f"context:{conversation_id}")
            if data:
                context = json.loads(data)
        else:
            context = self.memory_store.get(conversation_id)
        
        # Return context if found, otherwise return default context
        if context:
            return context
        
        # Return empty context if not found
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def update(self, conversation_id: str, query: str, results: Dict[str, Any]):
        """Update conversation context with new interaction."""
        context = self.get_context(conversation_id)
        
        # Add new message
        context["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "results": results,
            "hash": self._hash_message(query)
        })
        
        # Keep only last 50 messages to prevent context overflow
        if len(context["messages"]) > 50:
            context["messages"] = context["messages"][-50:]
        
        # Update metadata
        context["metadata"]["last_updated"] = datetime.now().isoformat()
        
        # Save context
        if hasattr(self, 'redis_client'):
            self.redis_client.setex(
                f"context:{conversation_id}",
                3600 * 24,  # 24 hour TTL
                json.dumps(context)
            )
        else:
            self.memory_store[conversation_id] = context
    
    def get_relevant_context(self, conversation_id: str, query: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get the most relevant context for a query."""
        context = self.get_context(conversation_id)
        messages = context.get("messages", [])
        
        # For now, return the most recent messages
        # In the future, this could use semantic similarity
        return messages[-max_messages:]
    
    def clear_context(self, conversation_id: str):
        """Clear context for a conversation."""
        if hasattr(self, 'redis_client'):
            self.redis_client.delete(f"context:{conversation_id}")
        else:
            self.memory_store.pop(conversation_id, None)
    
    def _hash_message(self, message: str) -> str:
        """Create a hash of a message for deduplication."""
        return hashlib.sha256(message.encode()).hexdigest()[:16]