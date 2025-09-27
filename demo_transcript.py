#!/usr/bin/env python3
"""
Demo script for the Adam NPC MCP System
Demonstrates the simplified FastAPI + FastMCP architecture
"""

import os
import requests
import time
import json
from datetime import datetime

def wait_for_server(url: str, max_attempts: int = 30) -> bool:
    """Wait for the MCP server to be ready."""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt == 0:
            print(f"⏳ Waiting for MCP server at {url}...")
        time.sleep(1)
    
    return False

def run_demo_conversation():
    """Run a demonstration conversation with Adam using the new FastAPI architecture."""
    
    print("=== Adam NPC MCP System Demo ===")
    print("FastAPI + FastMCP Architecture\n")
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️  WARNING: OpenAI API key not found.")
        print("   Demo will use the sample transcript instead.\n")
        show_sample_transcript()
        return
    
    # Server configuration
    server_url = "http://localhost:8000"
    client_url = "http://localhost:8001"
    
    # Check if MCP server is running
    if not wait_for_server(server_url):
        print(f"❌ MCP server not available at {server_url}")
        print("   Please start the server with: python start_server.py")
        print("   Showing sample transcript instead:\n")
        show_sample_transcript()
        return
    
    print(f"✅ MCP server ready at {server_url}")
    
    # Demo conversation flow
    demo_messages = [
        "Hello Adam, I've heard you are a wise sage. Can you introduce yourself?",
        "What can you tell me about the Northern Isles where you live?",
        "I'm interested in learning about magic. Can you share some wisdom?",
        "What are some popular gaming genres these days?",
        "How do you view the passage of time?",
        "Thank you for sharing your wisdom, Adam."
    ]
    
    print("🤖 Starting demo conversation...\n")
    
    # Reset conversation first
    try:
        requests.post(f"{server_url}/reset", timeout=10)
        print("🔄 Conversation reset\n")
    except Exception as e:
        print(f"⚠️  Could not reset conversation: {e}\n")
    
    # Run the conversation
    for i, user_message in enumerate(demo_messages, 1):
        try:
            print(f"👤 User: {user_message}")
            
            # Try using the client API if available, otherwise direct server calls
            try:
                response = requests.post(
                    f"{client_url}/chat",
                    json={"content": user_message},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    adam_response = result["response"]
                    used_tool = result.get("used_knowledge_tool", False)
                    
                    print(f"🧙 Adam: {adam_response}")
                    if used_tool:
                        print("   💡 [Adam consulted ancient knowledge]")
                else:
                    raise Exception(f"Client API error: {response.status_code}")
                    
            except Exception as client_error:
                # Fallback to direct server interaction
                print(f"   (Using direct MCP server calls)")
                
                # Add user message to context
                add_msg_response = requests.post(
                    f"{server_url}/add_message",
                    json={
                        "message": {
                            "role": "user",
                            "content": user_message,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=10
                )
                
                # Check if we should use knowledge tool
                if any(keyword in user_message.lower() for keyword in 
                       ["what", "tell me about", "magic", "gaming", "northern isles"]):
                    tool_response = requests.post(
                        f"{server_url}/tool_call",
                        json={"query": user_message},
                        timeout=10
                    )
                    if tool_response.status_code == 200:
                        knowledge = tool_response.json().get("result", "")
                        print(f"   💡 Knowledge found: {knowledge[:100]}...")
                
                # Simulate Adam's response (simplified for demo)
                adam_responses = [
                    "Greetings, traveler. I am Adam, a sage who has dwelled in the Northern Isles for many centuries, studying the ancient arts and gathering wisdom.",
                    "The Northern Isles... a mystical realm where magic flows through ley lines like rivers of starlight, and time itself bends to the will of ancient forces.",
                    "Magic, young one, is not mere trickery. It is the art of understanding the deep connections between all things, requiring respect for natural order.",
                    "Gaming genres... an interesting development in your modern world! I observe how these digital realms mirror the adventures and quests of old.",
                    "Time flows differently when you have lived as long as I have. Centuries pass like seasons, yet each moment holds infinite possibility.",
                    "May the wisdom of ages guide your path, dear friend. Until our paths cross again in the mists of time."
                ]
                
                adam_response = adam_responses[min(i-1, len(adam_responses)-1)]
                print(f"🧙 Adam: {adam_response}")
                
                # Add Adam's response to context
                requests.post(
                    f"{server_url}/add_message",
                    json={
                        "message": {
                            "role": "assistant", 
                            "content": adam_response,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=10
                )
            
            print()
            time.sleep(1)  # Brief pause between messages
            
        except Exception as e:
            print(f"❌ Error in conversation turn {i}: {e}")
            print()
    
    # Show conversation summary
    try:
        summary_response = requests.post(f"{server_url}/summarize_history", timeout=10)
        if summary_response.status_code == 200:
            summary = summary_response.json().get("summary", "")
            print("📝 Conversation Summary:")
            print(f"   {summary}")
        
        # Show final context
        context_response = requests.get(f"{server_url}/get_context", timeout=10)
        if context_response.status_code == 200:
            context = context_response.json()
            print(f"📊 Total messages: {len(context.get('messages', []))}")
            print(f"📊 Token count: {context.get('token_count', 0)}")
    except Exception as e:
        print(f"⚠️  Could not get conversation summary: {e}")
    
    print("\n✅ Demo completed successfully!")
    print("🚀 Try the interactive chat with: python mcp_client.py")

def show_sample_transcript():
    """Show the sample transcript when live demo isn't available."""
    try:
        with open("sample_transcript.txt", "r") as f:
            content = f.read()
        print("📋 Sample Conversation Transcript:")
        print("=" * 50)
        print(content)
        print("=" * 50)
        print("\n💡 To run live demo:")
        print("   1. Set OPENAI_API_KEY environment variable")
        print("   2. Start server: python start_server.py")
        print("   3. Run demo: python demo_transcript.py")
    except FileNotFoundError:
        print("📋 Sample transcript not found.")
        print("   Please run this demo with the MCP server running.")

def test_server_endpoints():
    """Test the MCP server endpoints."""
    server_url = "http://localhost:8000"
    
    print("🧪 Testing MCP Server Endpoints...")
    
    if not wait_for_server(server_url):
        print(f"❌ Server not available at {server_url}")
        return
    
    # Test health endpoint
    try:
        response = requests.get(f"{server_url}/health")
        print(f"✅ Health check: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test knowledge tool
    try:
        response = requests.post(
            f"{server_url}/tool_call",
            json={"query": "wisdom"}
        )
        result = response.json()
        print(f"✅ Knowledge tool: {result.get('result', '')[:100]}...")
    except Exception as e:
        print(f"❌ Knowledge tool failed: {e}")
    
    # Test reset
    try:
        response = requests.post(f"{server_url}/reset")
        print(f"✅ Reset: {response.json()}")
    except Exception as e:
        print(f"❌ Reset failed: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_server_endpoints()
    else:
        run_demo_conversation()