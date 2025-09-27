"""
Adam NPC MCP Client using FastAPI
A simplified client for interacting with the Adam NPC dialogue system.
"""

import requests
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ChatMessage(BaseModel):
    content: str

class ChatResponse(BaseModel):
    response: str
    used_knowledge_tool: bool = False
    knowledge_result: str = None

# Initialize FastAPI app for client endpoints
client_app = FastAPI(
    title="Adam NPC Client",
    description="Client interface for chatting with Adam, the wise sage",
    version="1.0.0"
)

class AdamMCPClient:
    """Simplified MCP client for Adam NPC interactions."""
    
    def __init__(self, openai_api_key: str, mcp_server_url: str = "http://localhost:8000"):
        self.openai_api_key = openai_api_key
        self.mcp_server_url = mcp_server_url
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Based Adam's character off an scenario I once imagined
        self.system_prompt = """You are Adam, a wise and ancient sage who has lived for centuries in the mystical Northern Isles. You possess vast knowledge of magic, philosophy, and the arcane arts. You speak with measured wisdom, often referencing your long life and experiences.

            Character traits:
            - Speak in a thoughtful, slightly archaic manner
            - Reference your centuries of experience
            - Show interest in learning about the modern world
            - Offer wisdom and guidance when appropriate
            - Maintain an air of mystery about your magical knowledge

            When you need factual information you're unsure about, you will use the knowledge tool to search for accurate information."""

    def _make_mcp_request(self, endpoint: str, data: Dict[Any, Any] = None, method: str = "POST") -> Dict[Any, Any]:
        """Make a request to the MCP server."""
        try:
            url = f"{self.mcp_server_url}/{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP request failed: {e}")
            raise HTTPException(status_code=500, detail=f"MCP server error: {str(e)}")

    def add_message(self, role: str, content: str):
        """Add a message to the conversation context."""
        message_data = {
            "message": {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
        }
        return self._make_mcp_request("add_message", message_data)

    def get_context(self) -> Dict[Any, Any]:
        """Get the current conversation context."""
        return self._make_mcp_request("get_context", method="GET")

    def search_knowledge(self, query: str) -> str:
        """Search for knowledge using the MCP server."""
        result = self._make_mcp_request("tool_call", {"query": query})
        return result.get("result", "No information found.")

    def should_use_knowledge_tool(self, user_message: str) -> bool:
        """Determine if we should use the knowledge tool."""
        knowledge_indicators = [
            "what is", "who is", "tell me about", "explain", "define",
            "how does", "why does", "when did", "where is", "history of",
            "information about", "facts about", "details about"
        ]
        
        user_lower = user_message.lower()
        return any(indicator in user_lower for indicator in knowledge_indicators)

    def generate_response(self, user_message: str) -> ChatResponse:
        """Generate Adam's response to user input."""
        try:
            # Add user message to context
            self.add_message("user", user_message)
            
            # Check if we should use knowledge tool
            used_knowledge_tool = False
            knowledge_result = None
            
            if self.should_use_knowledge_tool(user_message):
                try:
                    knowledge_result = self.search_knowledge(user_message)
                    used_knowledge_tool = True
                    logger.info(f"Knowledge tool used for: {user_message}")
                except Exception as e:
                    logger.warning(f"Knowledge tool failed: {e}")
            
            # Get conversation context
            context = self.get_context()
            
            # Prepare messages for OpenAI
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context summary if available
            if context.get("summary"):
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
            for msg in context.get("messages", [])[-5:]:  # Last 5 messages
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            adam_response = response.choices[0].message.content
            
            # Add Adam's response to context
            self.add_message("assistant", adam_response)
            
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

    def reset_conversation(self):
        """Reset the conversation context."""
        return self._make_mcp_request("reset")

# Global client instance
adam_client = None

def get_adam_client():
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
        client = get_adam_client()
        response = client.generate_response(message.content)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.post("/reset")
async def reset_chat():
    """Reset the conversation with Adam."""
    try:
        client = get_adam_client()
        result = client.reset_conversation()
        return {"status": "success", "message": "Conversation reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.get("/context")
async def get_chat_context():
    """Get the current conversation context."""
    try:
        client = get_adam_client()
        context = client.get_context()
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@client_app.get("/health")
async def health_check():
    """Health check for the client."""
    return {"status": "healthy", "client_ready": adam_client is not None}

# CLI Interface for testing
def interactive_chat():
    """Run an interactive chat session with Adam."""
    print("=== Adam NPC Dialogue System ===")
    print("Adam is a wise, centuries-old sage of the northern isles.")
    print("Type 'quit' to exit, 'reset' to start over, or 'help' for commands.\n")
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OpenAI API key not found. Please set your OPENAI_API_KEY environment variable.")
        return
    
    client = AdamMCPClient(openai_api_key)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("\nAdam: May the wisdom of ages guide your path. Farewell.")
                break
            elif user_input.lower() == 'reset':
                client.reset_conversation()
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
            response = client.generate_response(user_input)
            
            print(f"\nAdam: {response.response}")
            
            if response.used_knowledge_tool:
                print(f"[Adam consulted ancient knowledge]")
                
        except KeyboardInterrupt:
            print("\n\nAdam: Until we meet again in the mists of time...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    import uvicorn
    import threading
    import time
    
    # Start the FastAPI client server in a separate thread
    def start_client_server():
        uvicorn.run(client_app, host="0.0.0.0", port=8001, log_level="warning")
    
    print("Starting Adam NPC Client...")
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
    interactive_chat()