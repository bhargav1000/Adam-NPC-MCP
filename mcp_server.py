"""
Adam NPC MCP Server using FastMCP and FastAPI
A simplified Model Context Protocol server for managing conversation context and knowledge tools.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
import json
import tiktoken
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class AddMessageRequest(BaseModel):
    message: Message

class ToolCallRequest(BaseModel):
    query: str

class ConversationContext(BaseModel):
    messages: List[Message]
    summary: str
    token_count: int

# Initialize FastAPI app
app = FastAPI(
    title="Adam NPC MCP Server",
    description="A Model Context Protocol server for Adam, a wise NPC sage",
    version="1.0.0"
)

# In-memory storage for conversation context
conversation_memory: List[Message] = []
conversation_summary: str = ""
MAX_TOKENS = 4000

# Knowledge base for Adam's character
# Based this off an old character I once imagined
ADAM_KNOWLEDGE_BASE = {
    "northern isles": "The Northern Isles are a mystical archipelago shrouded in ancient magic, where Adam has dwelled for centuries studying the arcane arts.",
    "gaming genres": "Action, Adventure, RPG, Strategy, Simulation, Puzzle, Sports, Racing, Fighting, Shooter, Platform, Survival, Horror, and Indie games each offer unique experiences.",
    "magic": "Magic in the Northern Isles flows through ley lines and crystal formations, channeled through ancient runes and spoken incantations.",
    "wisdom": "True wisdom comes not from knowing all answers, but from understanding which questions to ask and when to listen.",
    "time": "Time flows differently in the Northern Isles - what seems like moments can be years, and centuries can pass like heartbeats."
}

def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except:
        # Fallback estimation
        return len(text.split()) * 1.3

def get_context_summary() -> str:
    """Get a summary of the current conversation context."""
    if not conversation_memory:
        return "No conversation history."
    
    total_tokens = sum(estimate_tokens(msg.content) for msg in conversation_memory)
    recent_messages = conversation_memory[-3:] if len(conversation_memory) > 3 else conversation_memory
    
    summary_parts = []
    if conversation_summary:
        summary_parts.append(f"Previous summary: {conversation_summary}")
    
    summary_parts.append("Recent messages:")
    for msg in recent_messages:
        summary_parts.append(f"- {msg.role}: {msg.content[:100]}...")
    
    return "\n".join(summary_parts)

def search_knowledge(query: str) -> str:
    """Search the knowledge base and Wikipedia for information."""
    query_lower = query.lower()
    
    # Check built-in knowledge base first
    for key, value in ADAM_KNOWLEDGE_BASE.items():
        if key.lower() in query_lower:
            return f"From Adam's ancient knowledge: {value}"
    
    # Fallback to Wikipedia search
    try:
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        headers = {"User-Agent": "Adam-NPC-MCP/1.0 (Educational)"}
        
        response = requests.get(search_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            extract = data.get("extract", "")
            if extract:
                return f"From the ancient scrolls (Wikipedia): {extract[:300]}..."
        
        # If direct page doesn't exist, try search
        search_api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "format": "json"
        }
        
        response = requests.get(search_api_url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            results = response.json()
            if len(results) > 1 and results[1]:
                return f"Found in the ancient scrolls: {results[1][0]} - {results[2][0] if len(results) > 2 and results[2] else 'A topic of great interest.'}"
    
    except Exception as e:
        logger.warning(f"Knowledge search failed: {e}")
    
    return f"The mists of time obscure this knowledge, but perhaps we can explore '{query}' together through conversation."

# FastAPI endpoints
@app.post("/add_message")
async def add_message(request: AddMessageRequest):
    """Add a message to the conversation context."""
    try:
        conversation_memory.append(request.message)
        
        # Manage token limit
        total_tokens = sum(estimate_tokens(msg.content) for msg in conversation_memory)
        
        if total_tokens > MAX_TOKENS:
            # Summarize and trim old messages
            global conversation_summary
            old_messages = conversation_memory[:-5]  # Keep last 5 messages
            summary_text = "\n".join([f"{msg.role}: {msg.content}" for msg in old_messages])
            conversation_summary = f"Previous conversation covered: {summary_text[:500]}..."
            conversation_memory[:] = conversation_memory[-5:]
        
        return {
            "status": "success",
            "message": "Message added to context",
            "token_count": sum(estimate_tokens(msg.content) for msg in conversation_memory)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_context")
async def get_context():
    """Retrieve the current conversation context."""
    return ConversationContext(
        messages=conversation_memory,
        summary=get_context_summary(),
        token_count=sum(estimate_tokens(msg.content) for msg in conversation_memory)
    )

@app.post("/tool_call")
async def tool_call(request: ToolCallRequest):
    """Handle knowledge tool calls."""
    try:
        result = search_knowledge(request.query)
        return {
            "status": "success",
            "query": request.query,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize_history")
async def summarize_history():
    """Summarize the conversation history."""
    if not conversation_memory:
        return {"summary": "No conversation to summarize."}
    
    summary = get_context_summary()
    return {"summary": summary}

@app.post("/reset")
async def reset():
    """Reset the conversation context."""
    global conversation_memory, conversation_summary
    conversation_memory.clear()
    conversation_summary = ""
    return {"status": "success", "message": "Conversation context reset"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "messages_count": len(conversation_memory),
        "summary_exists": bool(conversation_summary)
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Adam NPC MCP Server with FastAPI...")
    print("Server will be available at http://localhost:8000")
    print("API Documentation at http://localhost:8000/docs")
    print("MCP endpoints:")
    print("- POST /add_message - Add message to context")
    print("- GET /get_context - Get conversation context") 
    print("- POST /tool_call - Knowledge search")
    print("- POST /summarize_history - Get conversation summary")
    print("- POST /reset - Reset conversation")
    print("- GET /health - Health check")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)