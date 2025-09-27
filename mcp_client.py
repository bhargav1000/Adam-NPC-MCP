import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai
from pydantic import BaseModel
import logging
import httpx
import json
from fastapi_mcp_client import MCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for FastAPI endpoints
class ChatMessage(BaseModel):
    content: str

class ChatResponse(BaseModel):
    response: str
    used_knowledge_tool: bool = False
    knowledge_result: Optional[str] = None

# Simple client - no web interface needed

class AdamMCPClient:
    """MCP client for Adam NPC interactions using proper MCP protocol."""
    
    def __init__(self, openai_api_key: str, mcp_server_url: str = "http://localhost:8000"):
        self.openai_api_key = openai_api_key
        self.mcp_server_url = mcp_server_url
        self.base_server_url = mcp_server_url  # For HTTP fallback
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.mcp_client = None
        
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
            # Create proper MCP client
            self.mcp_client = MCPClient(self.mcp_server_url)
            await self.mcp_client.__aenter__()
            logger.info("✅ MCP protocol connection established")
            return self
        except Exception as e:
            logger.warning(f"⚠️  MCP connection failed, using HTTP fallback: {e}")
            self.mcp_client = None
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.mcp_client:
            await self.mcp_client.__aexit__(exc_type, exc_val, exc_tb)

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool via proper MCP client or HTTP fallback."""
        if self.mcp_client:
            try:
                # Use proper MCP protocol
                result = await self.mcp_client.call_operation(tool_name, arguments or {})
                logger.debug(f"MCP call successful: {tool_name}")
                return result
            except Exception as e:
                logger.warning(f"MCP call failed: {e}, falling back to HTTP")
        
        # Fallback to HTTP calls
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
        
        url = f"{self.base_server_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            if tool_name in ["get_context", "get_health_status"]:
                response = await client.get(url)
            else:
                response = await client.post(url, json=arguments or {})
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

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
                used_knowledge_tool=False,
                knowledge_result=None
            )

# Simple CLI client - no web endpoints needed

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
        # Check if server is running
        try:
            health = await client.get_health_status()
            print(f"✅ Server is running: {health['status']}")
        except Exception as e:
            print(f"❌ Cannot connect to MCP server at {client.mcp_server_url}")
            print(f"   Make sure the server is running: python mcp_server.py")
            print(f"   MCP endpoint should be available at /mcp")
            print(f"   HTTP fallback at {client.base_server_url}")
            return
        
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
    print("Starting Adam NPC MCP Client...")
    print("Connecting to MCP server at http://localhost:8000")
    print("Will use proper MCP protocol with HTTP fallback")
    print("Type 'quit' to exit, 'reset' to start over, or 'help' for commands.\n")
    
    # Start interactive chat directly
    start_interactive_chat()
