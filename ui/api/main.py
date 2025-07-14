from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
import json
import logging
import os

from agent.genesis_agent import GenesisAgent
from .models import ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global agent
    agent = GenesisAgent(llm_provider=os.getenv("LLM_PROVIDER", "openai"))
    logger.info("Genesis Agent initialized")
    yield
    # Shutdown
    if hasattr(agent.tool_registry, 'cleanup'):
        await agent.tool_registry.cleanup()

app = FastAPI(title="Genesis Agent API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "initialized" if agent else "not initialized"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message."""
    try:
        response = await agent.process_request(
            query=request.query,
            conversation_id=request.conversation_id
        )
        return ChatResponse(**response)
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(
            response=f"I encountered an error: {str(e)}",
            error=True
        )

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    await websocket.accept()
    conversation_id = str(uuid.uuid4())
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Stream response
            await websocket.send_json({
                "type": "start",
                "conversation_id": conversation_id
            })
            
            async for chunk in agent.process_request_stream(
                query=data["query"],
                conversation_id=conversation_id
            ):
                await websocket.send_json(chunk)
            
            await websocket.send_json({"type": "end"})
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)