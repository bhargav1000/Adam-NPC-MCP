"""
Adam NPC LangGraph Workflow
==========================

LangGraph-based dialogue orchestration for Adam, the wise sage NPC.
Integrates with the existing MCP server tools and provides structured workflow management.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import BaseModel
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State Management for Adam NPC Workflow
class AdamWorkflowState(TypedDict):
    """State object for Adam NPC conversation workflow."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_input: str
    context_summary: str
    knowledge_used: bool
    knowledge_result: Optional[str]
    needs_knowledge_search: bool
    adam_response: str
    conversation_metadata: Dict[str, Any]

class AdamNPCWorkflow:
    """LangGraph workflow orchestrator for Adam NPC dialogue system."""
    
    def __init__(self, openai_api_key: str, mcp_server_url: str = "http://localhost:8000"):
        self.openai_api_key = openai_api_key
        self.mcp_server_url = mcp_server_url
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.7,
            max_tokens=300
        )
        
        # Adam's system prompt
        self.adam_system_prompt = """You are Adam, a wise and ancient sage who has lived for centuries in the mystical Northern Isles. You possess vast knowledge of magic, philosophy, and the arcane arts. You speak with measured wisdom, often referencing your long life and experiences.

Character traits:
- Speak in a thoughtful, slightly archaic manner
- Reference your centuries of experience
- Show interest in learning about the modern world
- Offer wisdom and guidance when appropriate
- Maintain an air of mystery about your magical knowledge

When you have access to relevant knowledge from your search, incorporate it naturally into your response."""

        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for Adam NPC dialogue."""
        
        # Create the state graph
        workflow = StateGraph(AdamWorkflowState)
        
        # Add nodes for each step in the dialogue process
        workflow.add_node("input_processor", self._process_input)
        workflow.add_node("context_retriever", self._retrieve_context)
        workflow.add_node("knowledge_decider", self._decide_knowledge_search)
        workflow.add_node("knowledge_searcher", self._search_knowledge)
        workflow.add_node("response_generator", self._generate_response)
        workflow.add_node("context_updater", self._update_context)
        
        # Define the workflow edges
        workflow.add_edge(START, "input_processor")
        workflow.add_edge("input_processor", "context_retriever")
        workflow.add_edge("context_retriever", "knowledge_decider")
        
        # Conditional edge for knowledge search
        workflow.add_conditional_edges(
            "knowledge_decider",
            self._should_search_knowledge,
            {
                True: "knowledge_searcher",
                False: "response_generator"
            }
        )
        
        workflow.add_edge("knowledge_searcher", "response_generator")
        workflow.add_edge("response_generator", "context_updater")
        workflow.add_edge("context_updater", END)
        
        return workflow.compile()
    
    async def _process_input(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Process user input and prepare it for the workflow."""
        logger.info(f"Processing user input: {state['user_input'][:50]}...")
        
        # Add user message to the conversation
        user_message = HumanMessage(content=state["user_input"])
        
        return {
            "messages": [user_message],
            "conversation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "input_length": len(state["user_input"])
            }
        }
    
    async def _retrieve_context(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Retrieve conversation context from MCP server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.mcp_server_url}/get_context")
                if response.status_code == 200:
                    context_data = response.json()
                    summary = context_data.get("summary", "No conversation history.")
                    logger.info("Retrieved conversation context successfully")
                    return {"context_summary": summary}
                else:
                    logger.warning(f"Failed to retrieve context: {response.status_code}")
                    return {"context_summary": "No conversation history available."}
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return {"context_summary": "Error accessing conversation history."}
    
    async def _decide_knowledge_search(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Decide if knowledge search is needed based on user input."""
        user_input = state["user_input"].lower()
        
        # Knowledge indicators
        knowledge_indicators = [
            "what is", "who is", "tell me about", "explain", "define",
            "how does", "why does", "when did", "where is", "history of",
            "information about", "facts about", "details about",
            "magic", "northern isles", "wisdom", "time", "gaming"
        ]
        
        needs_search = any(indicator in user_input for indicator in knowledge_indicators)
        logger.info(f"Knowledge search needed: {needs_search}")
        
        return {"needs_knowledge_search": needs_search}
    
    def _should_search_knowledge(self, state: AdamWorkflowState) -> bool:
        """Conditional edge function to determine if knowledge search is needed."""
        return state.get("needs_knowledge_search", False)
    
    async def _search_knowledge(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Search for knowledge using MCP server knowledge tool."""
        try:
            query_data = {"query": state["user_input"]}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/knowledge_search",
                    json=query_data
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    knowledge_result = result_data.get("result", "No knowledge found.")
                    logger.info("Knowledge search completed successfully")
                    
                    return {
                        "knowledge_used": True,
                        "knowledge_result": knowledge_result
                    }
                else:
                    logger.warning(f"Knowledge search failed: {response.status_code}")
                    return {
                        "knowledge_used": False,
                        "knowledge_result": None
                    }
        except Exception as e:
            logger.error(f"Error during knowledge search: {e}")
            return {
                "knowledge_used": False,
                "knowledge_result": None
            }
    
    async def _generate_response(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Generate Adam's response using OpenAI with context and knowledge."""
        try:
            # Prepare the conversation messages
            messages = [SystemMessage(content=self.adam_system_prompt)]
            
            # Add context if available
            if state.get("context_summary"):
                context_msg = SystemMessage(
                    content=f"Conversation context: {state['context_summary']}"
                )
                messages.append(context_msg)
            
            # Add knowledge if available
            if state.get("knowledge_result"):
                knowledge_msg = SystemMessage(
                    content=f"Relevant knowledge: {state['knowledge_result']}"
                )
                messages.append(knowledge_msg)
            
            # Add the current conversation messages
            messages.extend(state["messages"])
            
            # Generate response using OpenAI
            response = await self.llm.ainvoke(messages)
            adam_response = response.content
            
            logger.info("Generated Adam's response successfully")
            
            return {"adam_response": adam_response}
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "adam_response": "I apologize, but something went wrong while processing your message. Could you try again?"
            }
    
    async def _update_context(self, state: AdamWorkflowState) -> Dict[str, Any]:
        """Update conversation context on MCP server."""
        try:
            # Add user message to context
            user_msg_data = {
                "role": "user",
                "content": state["user_input"],
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.mcp_server_url}/add_message",
                    json=user_msg_data
                )
            
            # Add Adam's response to context
            adam_msg_data = {
                "role": "assistant", 
                "content": state["adam_response"],
                "timestamp": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.mcp_server_url}/add_message",
                    json=adam_msg_data
                )
            
            logger.info("Updated conversation context successfully")
            
            return {
                "conversation_metadata": {
                    **state.get("conversation_metadata", {}),
                    "context_updated": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating context: {e}")
            return {
                "conversation_metadata": {
                    **state.get("conversation_metadata", {}),
                    "context_updated": False
                }
            }
    
    async def process_dialogue(self, user_input: str) -> Dict[str, Any]:
        """Process a dialogue turn through the LangGraph workflow."""
        
        # Initial state
        initial_state = AdamWorkflowState(
            messages=[],
            user_input=user_input,
            context_summary="",
            knowledge_used=False,
            knowledge_result=None,
            needs_knowledge_search=False,
            adam_response="",
            conversation_metadata={}
        )
        
        # Execute the workflow
        try:
            result = await self.workflow.ainvoke(initial_state)
            
            return {
                "response": result["adam_response"],
                "used_knowledge_tool": result.get("knowledge_used", False),
                "knowledge_result": result.get("knowledge_result"),
                "metadata": result.get("conversation_metadata", {})
            }
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                "response": "I apologize, but something went wrong while processing your message. Could you try again?",
                "used_knowledge_tool": False,
                "knowledge_result": None,
                "metadata": {"error": str(e)}
            }

# Factory function for creating the workflow
def create_adam_workflow(openai_api_key: str, mcp_server_url: str = "http://localhost:8000") -> AdamNPCWorkflow:
    """Create and return an Adam NPC LangGraph workflow instance."""
    return AdamNPCWorkflow(openai_api_key, mcp_server_url)

# Example usage and testing
async def test_workflow():
    """Test the Adam NPC LangGraph workflow."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return
    
    workflow = create_adam_workflow(api_key)
    
    # Test dialogue
    test_inputs = [
        "Hello Adam, how are you?",
        "Tell me about magic in the Northern Isles",
        "What wisdom can you share about time?"
    ]
    
    for user_input in test_inputs:
        print(f"\n🧪 Testing: {user_input}")
        result = await workflow.process_dialogue(user_input)
        print(f"🧙‍♂️ Adam: {result['response']}")
        if result['used_knowledge_tool']:
            print(f"📚 [Used knowledge tool]")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_workflow())
