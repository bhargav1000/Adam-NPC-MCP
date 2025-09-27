"""
Adam NPC MCP Server using proper MCP protocol
Model Context Protocol implementation with JSON-RPC support using the official MCP library.
"""

from mcp.server import FastMCP
from mcp import types
from typing import List, Dict, Any, Optional
import requests
import json
import tiktoken
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = FastMCP(
    name="Adam NPC System"
)

# In-memory storage for conversation context
conversation_memory: List[Dict[str, Any]] = []
conversation_summary: str = ""
MAX_TOKENS = 4000

# Knowledge base for Adam's character
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
    
    summary_parts = []
    if conversation_summary:
        summary_parts.append(f"Previous summary: {conversation_summary}")
    
    recent_messages = conversation_memory[-3:] if len(conversation_memory) > 3 else conversation_memory
    summary_parts.append("Recent messages:")
    for msg in recent_messages:
        summary_parts.append(f"- {msg['role']}: {msg['content'][:100]}...")
    
    return "\n".join(summary_parts)

def search_knowledge_tool(query: str) -> str:
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

# MCP Tools
@server.tool()
async def add_message(role: str, content: str, timestamp: Optional[str] = None) -> str:
    """Add a message to the conversation context."""
    global conversation_memory, conversation_summary
    
    message = {
        "role": role,
        "content": content,
        "timestamp": timestamp or datetime.now().isoformat()
    }
    
    conversation_memory.append(message)
    
    # Manage token limit
    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    
    if total_tokens > MAX_TOKENS:
        # Summarize and trim old messages
        old_messages = conversation_memory[:-5]  # Keep last 5 messages
        summary_text = "\n".join([f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in old_messages])
        conversation_summary = f"Previous conversation covered: {summary_text[:500]}..."
        conversation_memory[:] = conversation_memory[-5:]
    
    result = {
        "status": "success",
        "message": "Message added to context",
        "token_count": sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    }
    return json.dumps(result)

@server.tool()
async def get_context() -> str:
    """Retrieve the current conversation context."""
    result = {
        "messages": conversation_memory,
        "summary": get_context_summary(),
        "token_count": sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    }
    return json.dumps(result)

@server.tool()
async def knowledge_search(query: str) -> str:
    """Search the knowledge base and Wikipedia for information about a topic."""
    result_text = search_knowledge_tool(query)
    result = {
        "status": "success",
        "query": query,
        "result": result_text
    }
    return json.dumps(result)

@server.tool()
async def summarize_history() -> str:
    """Summarize the conversation history."""
    if not conversation_memory:
        result = {"summary": "No conversation to summarize."}
    else:
        summary = get_context_summary()
        result = {"summary": summary}
    return json.dumps(result)

@server.tool()
async def reset_conversation() -> str:
    """Reset the conversation context."""
    global conversation_memory, conversation_summary
    conversation_memory.clear()
    conversation_summary = ""
    result = {"status": "success", "message": "Conversation context reset"}
    return json.dumps(result)

@server.tool()
async def get_health_status() -> str:
    """Check the health status of the MCP server."""
    result = {
        "status": "healthy",
        "messages_count": len(conversation_memory),
        "summary_exists": bool(conversation_summary),
        "adam_knowledge_topics": list(ADAM_KNOWLEDGE_BASE.keys())
    }
    return json.dumps(result)

# MCP Resources
@server.resource("adam://character/profile")
async def adam_character_profile() -> str:
    """Get Adam's character profile and background."""
    profile = {
        "name": "Adam",
        "title": "Sage of the Northern Isles",
        "age": "Centuries old",
        "background": "A wise and ancient sage who has dwelled for centuries in the mystical Northern Isles, studying the arcane arts and gathering wisdom.",
        "personality": {
            "speech_style": "Thoughtful, slightly archaic manner",
            "interests": ["Magic", "Philosophy", "Arcane arts", "Ancient wisdom", "Modern world curiosities"],
            "traits": ["Wise", "Patient", "Mysterious", "Knowledgeable", "Curious about modern times"]
        },
        "knowledge_areas": list(ADAM_KNOWLEDGE_BASE.keys()),
        "origin": "Based on a character scenario once imagined by the creator"
    }
    
    return json.dumps(profile, indent=2)

if __name__ == "__main__":
    print("🚀 Starting Adam NPC MCP Server with proper MCP protocol...")
    print("📡 MCP JSON-RPC Server with protocol compliance")
    print("🔧 Available MCP tools:")
    print("- add_message: Add message to conversation context")
    print("- get_context: Get conversation context") 
    print("- knowledge_search: Search Adam's knowledge and Wikipedia")
    print("- summarize_history: Get conversation summary")
    print("- reset_conversation: Reset conversation")
    print("- get_health_status: Check server health")
    print("\n📚 Available MCP resources:")
    print("- adam://character/profile: Adam's character information")
    print("\n⚡ Starting server...")
    
    # Start the MCP server - this will auto-detect the transport
    server.run()
