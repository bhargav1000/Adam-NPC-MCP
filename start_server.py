#!/usr/bin/env python3
"""
Simple startup script for the Adam NPC MCP Server
Uses FastMCP for proper Model Context Protocol implementation
"""

import sys
import os

def main():
    """Start the Adam NPC MCP Server."""
    print("🚀 Starting Adam NPC MCP Server...")
    print("📡 MCP Server will be available for client connections")
    print("🔧 MCP tools: add_message, get_context, knowledge_search, etc.")
    print("📚 MCP resources: adam://character/profile")
    print("\n⚡ Press Ctrl+C to stop the server\n")
    
    try:
        # Import and run the FastMCP server
        from mcp_server import server
        
        # Run the MCP server (will auto-detect transport)
        server.run()
    except KeyboardInterrupt:
        print("\n👋 Adam NPC MCP Server shutting down...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()