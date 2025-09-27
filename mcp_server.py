"""
Adam NPC MCP Server using FastMCP
A proper Model Context Protocol server for managing conversation context and knowledge tools.
"""

from fastmcp import FastMCP, Context
from typing import List, Dict, Any, Optional
import requests
import json
import tiktoken
import logging
from datetime import datetime
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
server = FastMCP("Adam NPC System")

# In-memory storage for conversation context
conversation_memory: List[Dict[str, Any]] = []
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
    
    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    recent_messages = conversation_memory[-3:] if len(conversation_memory) > 3 else conversation_memory
    
    summary_parts = []
    if conversation_summary:
        summary_parts.append(f"Previous summary: {conversation_summary}")
    
    summary_parts.append("Recent messages:")
    for msg in recent_messages:
        content = msg.get("content", "")[:100]
        summary_parts.append(f"- {msg.get('role', 'unknown')}: {content}...")
    
    return "\n".join(summary_parts)

@server.tool
async def add_message(role: str, content: str, timestamp: Optional[str] = None, ctx: Context = None) -> dict:
    """Add a message to the conversation context."""
    if ctx:
        await ctx.info(f"Adding {role} message to conversation context")
    
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
        global conversation_summary
        old_messages = conversation_memory[:-5]  # Keep last 5 messages
        summary_text = "\n".join([f"{msg.get('role', '')}: {msg.get('content', '')}" for msg in old_messages])
        conversation_summary = f"Previous conversation covered: {summary_text[:500]}..."
        conversation_memory[:] = conversation_memory[-5:]
        
        if ctx:
            await ctx.info("Conversation summarized due to token limit")
    
    return {
        "status": "success",
        "message": "Message added to context",
        "token_count": sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    }

@server.tool
async def get_context(ctx: Context = None) -> dict:
    """Retrieve the current conversation context."""
    if ctx:
        await ctx.info("Retrieving conversation context")
    
    return {
        "messages": conversation_memory,
        "summary": get_context_summary(),
        "token_count": sum(estimate_tokens(msg.get("content", "")) for msg in conversation_memory)
    }

@server.tool
async def knowledge_search(query: str, ctx: Context = None) -> dict:
    """Search the knowledge base and Wikipedia for information about a topic."""
    if ctx:
        await ctx.info(f"Searching knowledge for: {query}")
    
    query_lower = query.lower()
    
    # Check built-in knowledge base first
    for key, value in ADAM_KNOWLEDGE_BASE.items():
        if key.lower() in query_lower:
            result = f"From Adam's ancient knowledge: {value}"
            if ctx:
                await ctx.info(f"Found knowledge in Adam's memory: {key}")
            return {
                "status": "success",
                "query": query,
                "result": result,
                "source": "adam_knowledge"
            }
    
    # Fallback to Wikipedia search
    if ctx:
        await ctx.info("Searching ancient scrolls (Wikipedia)")
    
    try:
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        headers = {"User-Agent": "Adam-NPC-MCP/1.0 (Educational)"}
        
        response = requests.get(search_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            extract = data.get("extract", "")
            if extract:
                result = f"From the ancient scrolls (Wikipedia): {extract[:300]}..."
                return {
                    "status": "success",
                    "query": query,
                    "result": result,
                    "source": "wikipedia"
                }
        
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
                result = f"Found in the ancient scrolls: {results[1][0]} - {results[2][0] if len(results) > 2 and results[2] else 'A topic of great interest.'}"
                return {
                    "status": "success",
                    "query": query,
                    "result": result,
                    "source": "wikipedia_search"
                }
    
    except Exception as e:
        if ctx:
            await ctx.warning(f"Knowledge search failed: {e}")
        logger.warning(f"Knowledge search failed: {e}")
    
    result = f"The mists of time obscure this knowledge, but perhaps we can explore '{query}' together through conversation."
    return {
        "status": "success",
        "query": query,
        "result": result,
        "source": "fallback"
    }

@server.tool
async def summarize_history(ctx: Context = None) -> dict:
    """Summarize the conversation history."""
    if ctx:
        await ctx.info("Summarizing conversation history")
    
    if not conversation_memory:
        return {"summary": "No conversation to summarize."}
    
    summary = get_context_summary()
    return {"summary": summary}

@server.tool
async def reset_conversation(ctx: Context = None) -> dict:
    """Reset the conversation context."""
    if ctx:
        await ctx.info("Resetting conversation context")
    
    global conversation_memory, conversation_summary
    conversation_memory.clear()
    conversation_summary = ""
    return {"status": "success", "message": "Conversation context reset"}

@server.tool
async def get_health_status(ctx: Context = None) -> dict:
    """Check the health status of the MCP server."""
    if ctx:
        await ctx.info("Checking server health")
    
    return {
        "status": "healthy",
        "messages_count": len(conversation_memory),
        "summary_exists": bool(conversation_summary),
        "adam_knowledge_topics": list(ADAM_KNOWLEDGE_BASE.keys())
    }

# Optional: Add a resource for Adam's character profile
@server.resource("adam://character/profile")
async def adam_character_profile(ctx: Context = None) -> str:
    """Get Adam's character profile and background."""
    if ctx:
        await ctx.info("Accessing Adam's character profile")
    
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
    print("Starting Adam NPC MCP Server with FastMCP...")
    print("Available MCP tools:")
    print("- add_message: Add message to conversation context")
    print("- get_context: Get conversation context") 
    print("- knowledge_search: Search Adam's knowledge and Wikipedia")
    print("- summarize_history: Get conversation summary")
    print("- reset_conversation: Reset conversation")
    print("- get_health_status: Check server health")
    print("\nAvailable MCP resources:")
    print("- adam://character/profile: Adam's character information")
    print("\nStarting server...")
    
    # Run the MCP server
    server.run()