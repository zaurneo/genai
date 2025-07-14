from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChatRequest(BaseModel):
    query: str
    conversation_id: str

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[Dict[str, Any]] = None
    error: bool = False

class StreamChunk(BaseModel):
    type: str  # "status", "content", "error", "end"
    chunk: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None