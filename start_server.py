#!/usr/bin/env python3
"""
Simple startup script for the Adam NPC MCP Server
Uses FastAPI and FastMCP for simplified architecture
"""

import uvicorn
import sys
import os

def main():
    """Start the Adam NPC MCP Server."""
    print("🚀 Starting Adam NPC MCP Server...")
    print("📡 Server will be available at: http://localhost:8000")
    print("📚 API Documentation at: http://localhost:8000/docs")
    print("🔍 Health check at: http://localhost:8000/health")
    print("\n⚡ Press Ctrl+C to stop the server\n")
    
    try:
        # Import the FastAPI app from mcp_server
        from mcp_server import app
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=True  # Enable auto-reload for development
        )
    except KeyboardInterrupt:
        print("\n👋 Adam NPC MCP Server shutting down...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()