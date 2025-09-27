"""
Adam NPC MCP Client using MCP JSON-RPC protocol
A proper MCP client for interacting with the Adam NPC dialogue system.
"""

import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import openai
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp import types
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for FastAPI endpoints
class ChatMessage(BaseModel):
    content: str

class ChatResponse(BaseModel):
    response: str
    used_knowledge_tool: bool = False
    knowledge_result: str = None

# Initialize FastAPI app for web interface
client_app = FastAPI(
    title="Adam NPC Client",
    description="Client interface for chatting with Adam, the wise sage",
    version="1.0.0"
)

class AdamMCPClient:
    """MCP client for Adam NPC interactions using proper MCP JSON-RPC protocol."""
    
    def __init__(self, openai_api_key: str, mcp_server_url: str = "http://localhost:8000"):
        self.openai_api_key = openai_api_key
        self.mcp_server_url = mcp_server_url
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.session = None
        
        self.system_prompt = """You are Adam, a wise and ancient sage who has lived for centuries in the mystical Northern Isles. You possess vast knowledge of magic, philosophy, and the arcane arts. You speak with measured wisdom, often referencing your long life and experiences.

        Character traits:
        - Speak in a thoughtful, slightly archaic manner
        - Reference your centuries of experience
        - Show interest in learning about the modern world
        - Offer wisdom and guidance when appropriate
        - Maintain an air of mystery about your magical knowledge

        When you need factual information you're unsure about, you will use the knowledge tool to search for accurate information."""

    async def __aenter__(self):
        """Async context manager entry - establish MCP connection."""
        try:
            # Try to connect to MCP server via SSE transport
            self.session = await sse_client(self.mcp_server_url).__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            logger.info("✅ Connected to MCP server successfully")
            return self
        except Exception as e:
            logger.warning(f"⚠️  MCP connection failed, using HTTP fallback: {e}")
            # Fallback to direct HTTP calls if MCP connection fails
            self.session = None
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool via JSON-RPC protocol."""
        if self.session:
            try:
                # Use proper MCP tool calling
                result = await self.session.call_tool(
                    name=tool_name,
                    arguments=arguments or {}
                )
                return result.content[0].text if result.content else {}
            except Exception as e:
                logger.warning(f"MCP tool call failed: {e}, falling back to HTTP")
        
        # Fallback to direct HTTP calls
        return await self._http_fallback(tool_name, arguments)

    async def _http_fallback(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback to direct HTTP calls when MCP fails."""
        endpoint_map = {
            "add_message": "/add_message",
            "get_context": "/get_context", 
            "knowledge_search": "/knowledge_search",
            "reset_conversation": "/reset_conversation",
            "get_health_status": "/health"
        }
        
        endpoint = endpoint_map.get(tool_name)
        if not endpoint:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        url = f"{self.mcp_server_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            if tool_name in ["get_context", "get_health_status"]:
                response = await client.get(url)
            else:
                response = await client.post(url, json=arguments or {})
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    async def add_message(self, role: str, content: str):
        """Add a message to the conversation context."""
        return await self._call_mcp_tool("add_message", {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    async def get_context(self) -> Dict[Any, Any]:
        """Get the current conversation context."""
        return await self._call_mcp_tool("get_context", {})

    async def search_knowledge(self, query: str) -> str:
        """Search for knowledge using the MCP server."""
        result = await self._call_mcp_tool("knowledge_search", {"query": query})
        if isinstance(result, dict):
            return result.get("result", "No information found.")
        return str(result)

    async def reset_conversation(self):
        """Reset the conversation context."""
        return await self._call_mcp_tool("reset_conversation", {})

    async def get_health_status(self):
        """Get server health status."""
        return await self._call_mcp_tool("get_health_status", {})

    def should_use_knowledge_tool(self, user_message: str) -> bool:
        """Determine if we should use the knowledge tool."""
        knowledge_indicators = [
            "what is", "who is", "tell me about", "explain", "define",
            "how does", "why does", "when did", "where is", "history of",
            "information about", "facts about", "details about"
        ]
        
        user_lower = user_message.lower()
        return any(indicator in user_lower for indicator in knowledge_indicators)

    async def generate_response(self, user_message: str) -> ChatResponse:
        """Generate Adam's response to user input."""
        try:
            # Add user message to context
            await self.add_message("user", user_message)
            
            # Check if we should use knowledge tool
            used_knowledge_tool = False
            knowledge_result = None
            
            if self.should_use_knowledge_tool(user_message):
                try:
                    knowledge_result = await self.search_knowledge(user_message)
                    used_knowledge_tool = True
                    logger.info(f"Knowledge tool used for: {user_message}")
                except Exception as e:
                    logger.warning(f"Knowledge tool failed: {e}")
            
            # Get conversation context
            context = await self.get_context()
            
            # Prepare messages for OpenAI
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context summary if available
            if isinstance(context, dict) and context.get("summary"):
                messages.append({
                    "role": "system", 
                    "content": f"Conversation context: {context['summary']}"
                })
            
            # Add knowledge if we found any
            if knowledge_result:
                messages.append({
                    "role": "system",
                    "content": f"Relevant knowledge: {knowledge_result}"
                })
            
            # Add recent conversation history
            if isinstance(context, dict) and context.get("messages"):
                for msg in context["messages"][-5:]:  # Last 5 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            adam_response = response.choices[0].message.content
            
            # Add Adam's response to context
            await self.add_message("assistant", adam_response)
            
            return ChatResponse(
                response=adam_response,
                used_knowledge_tool=used_knowledge_tool,
                knowledge_result=knowledge_result
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ChatResponse(
                response="I apologize, but something went wrong while processing your message. Could you try again?",
                used_knowledge_tool=False
            )

# Global client instance
adam_client = None

async def get_adam_client():
    """Get or create the Adam client instance."""
    global adam_client
    if adam_client is None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        adam_client = AdamMCPClient(openai_api_key)
    return adam_client

# FastAPI endpoints for the client
@client_app.post("/chat", response_model=ChatResponse)
async def chat_with_adam(message: ChatMessage):
    """Chat with Adam NPC."""
    try:
        client = await get_adam_client()
        async with client:
            response = await client.generate_response(message.content)
            return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.post("/reset")
async def reset_chat():
    """Reset the conversation with Adam."""
    try:
        client = await get_adam_client()
        async with client:
            await client.reset_conversation()
            return {"status": "success", "message": "Conversation reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.get("/context")
async def get_chat_context():
    """Get the current conversation context."""
    try:
        client = await get_adam_client()
        async with client:
            context = await client.get_context()
            return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.get("/health")
async def health_check():
    """Health check for the client and MCP server."""
    try:
        client = await get_adam_client()
        async with client:
            server_health = await client.get_health_status()
            return {
                "client_status": "healthy",
                "server_health": server_health
            }
    except Exception as e:
        return {
            "client_status": "error",
            "error": str(e)
        }

# CLI Interface for testing
async def interactive_chat():
    """Run an interactive chat session with Adam using MCP."""
    print("=== Adam NPC MCP Dialogue System ===")
    print("Adam is a wise, centuries-old sage of the northern isles.")
    print("Type 'quit' to exit, 'reset' to start over, or 'help' for commands.\n")
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OpenAI API key not found. Please set your OPENAI_API_KEY environment variable.")
        return
    
    client = AdamMCPClient(openai_api_key)
    
    async with client:
        # Test MCP connection
        try:
            health = await client.get_health_status()
            print(f"✅ Connected to MCP server: {health}")
        except Exception as e:
            print(f"⚠️  MCP connection failed, using HTTP fallback: {e}")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("\nAdam: May the wisdom of ages guide your path. Farewell.")
                    break
                elif user_input.lower() == 'reset':
                    await client.reset_conversation()
                    print("\n[Conversation reset]")
                    continue
                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("- Type any message to chat with Adam")
                    print("- 'reset' - Start a new conversation")
                    print("- 'quit' or 'exit' - End the session")
                    continue
                elif not user_input:
                    continue
                
                # Generate response
                response = await client.generate_response(user_input)
                
                print(f"\nAdam: {response.response}")
                
                if response.used_knowledge_tool:
                    print(f"[Adam consulted ancient knowledge]")
                    
            except KeyboardInterrupt:
                print("\n\nAdam: Until we meet again in the mists of time...")
                break
            except Exception as e:
                print(f"\nError: {e}")

def start_interactive_chat():
    """Start the interactive chat (sync wrapper)."""
    asyncio.run(interactive_chat())

if __name__ == "__main__":
    import uvicorn
    import threading
    import time
    
    # Start the FastAPI client server in a separate thread
    def start_client_server():
        uvicorn.run(client_app, host="0.0.0.0", port=8001, log_level="warning")
    
    print("Starting Adam NPC MCP Client...")
    print("Client API will be available at http://localhost:8001")
    print("Endpoints:")
    print("- POST /chat - Chat with Adam")
    print("- POST /reset - Reset conversation")
    print("- GET /context - Get conversation context")
    print("- GET /health - Health check")
    print("\nStarting interactive CLI in 2 seconds...")
    
    # Start server in background
    server_thread = threading.Thread(target=start_client_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    
    # Start interactive chat
    start_interactive_chat()
