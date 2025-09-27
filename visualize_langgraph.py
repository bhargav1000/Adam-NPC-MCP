#!/usr/bin/env python3
"""
Script to visualize the Adam NPC LangGraph workflow and save the output to files.
Creates both a network diagram and a detailed flow chart.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import networkx as nx
import numpy as np
from datetime import datetime

def create_workflow_network_diagram():
    """Create a network-style diagram of the LangGraph workflow."""
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes with their properties
    nodes = {
        'InputNode': {'pos': (0, 5), 'color': '#E8F5E8', 'desc': 'Process\nUser Input'},
        'CheckContextNode': {'pos': (0, 4), 'color': '#E8F0FF', 'desc': 'Retrieve\nContext'},
        'ToolDecisionNode': {'pos': (0, 3), 'color': '#FFF8E8', 'desc': 'Decide\nTool Usage'},
        'ToolCallNode': {'pos': (-1.5, 2), 'color': '#FFE8E8', 'desc': 'Execute\nTool Call'},
        'PromptAssemblyNode': {'pos': (0, 1), 'color': '#F0E8FF', 'desc': 'Assemble\nPrompt'},
        'LLMNode': {'pos': (0, 0), 'color': '#E8FFE8', 'desc': 'Generate\nResponse'},
        'OutputNode': {'pos': (0, -1), 'color': '#E8F8FF', 'desc': 'Update &\nReturn'}
    }
    
    # Add nodes to graph
    for node, props in nodes.items():
        G.add_node(node, **props)
    
    # Add edges
    edges = [
        ('InputNode', 'CheckContextNode'),
        ('CheckContextNode', 'ToolDecisionNode'),
        ('ToolDecisionNode', 'ToolCallNode'),
        ('ToolDecisionNode', 'PromptAssemblyNode'),
        ('ToolCallNode', 'PromptAssemblyNode'),
        ('PromptAssemblyNode', 'LLMNode'),
        ('LLMNode', 'OutputNode')
    ]
    
    G.add_edges_from(edges)
    
    # Create the plot
    fig, ax = plt.subplots(1, 1, figsize=(12, 14))
    
    # Get positions
    pos = nx.get_node_attributes(G, 'pos')
    
    # Draw nodes
    for node, (x, y) in pos.items():
        color = nodes[node]['color']
        desc = nodes[node]['desc']
        
        # Create fancy box
        bbox = FancyBboxPatch(
            (x-0.4, y-0.2), 0.8, 0.4,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor='#333333',
            linewidth=1.5
        )
        ax.add_patch(bbox)
        
        # Add text
        ax.text(x, y, f"{node}\n{desc}", 
                ha='center', va='center', 
                fontsize=9, fontweight='bold',
                wrap=True)
    
    # Draw edges
    for edge in G.edges():
        start_pos = pos[edge[0]]
        end_pos = pos[edge[1]]
        
        # Special handling for conditional edge
        if edge[0] == 'ToolDecisionNode':
            if edge[1] == 'ToolCallNode':
                # Draw curved arrow for "Yes" path
                ax.annotate('', xy=(end_pos[0]+0.3, end_pos[1]+0.2), 
                           xytext=(start_pos[0]-0.3, start_pos[1]-0.2),
                           arrowprops=dict(arrowstyle='->', lw=2, color='red',
                                         connectionstyle="arc3,rad=-0.3"))
                ax.text(start_pos[0]-0.8, start_pos[1]-0.5, 'YES\n(Tool Needed)', 
                       ha='center', va='center', fontsize=8, color='red', fontweight='bold')
            else:
                # Draw straight arrow for "No" path
                ax.annotate('', xy=(end_pos[0], end_pos[1]+0.2), 
                           xytext=(start_pos[0], start_pos[1]-0.2),
                           arrowprops=dict(arrowstyle='->', lw=2, color='green'))
                ax.text(start_pos[0]+0.8, start_pos[1]-0.5, 'NO\n(Skip Tools)', 
                       ha='center', va='center', fontsize=8, color='green', fontweight='bold')
        else:
            # Regular straight arrows
            ax.annotate('', xy=(end_pos[0], end_pos[1]+0.2), 
                       xytext=(start_pos[0], start_pos[1]-0.2),
                       arrowprops=dict(arrowstyle='->', lw=1.5, color='#333333'))
    
    # Add title and labels
    ax.set_title('Adam NPC LangGraph Workflow\nNode Execution Flow', 
                fontsize=16, fontweight='bold', pad=20)
    
    # Add legend
    legend_elements = [
        patches.Patch(color='#E8F5E8', label='Input Processing'),
        patches.Patch(color='#E8F0FF', label='Context Management'),
        patches.Patch(color='#FFF8E8', label='Decision Logic'),
        patches.Patch(color='#FFE8E8', label='Tool Execution'),
        patches.Patch(color='#F0E8FF', label='Prompt Assembly'),
        patches.Patch(color='#E8FFE8', label='LLM Generation'),
        patches.Patch(color='#E8F8FF', label='Output Processing')
    ]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
    
    # Set axis properties
    ax.set_xlim(-2.5, 1.5)
    ax.set_ylim(-2, 6)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ax.text(0, -1.8, f"Generated: {timestamp}", ha='center', va='center', 
           fontsize=8, style='italic', alpha=0.7)
    
    plt.tight_layout()
    return fig

def create_detailed_flow_chart():
    """Create a detailed flow chart with state transitions."""
    
    fig, ax = plt.subplots(1, 1, figsize=(16, 20))
    
    # Define the flow steps with detailed information
    steps = [
        {
            'name': 'START',
            'pos': (8, 19),
            'size': (1.5, 0.8),
            'color': '#90EE90',
            'text': 'User Input\nReceived',
            'details': 'e.g., "What are gaming genres?"'
        },
        {
            'name': 'InputNode',
            'pos': (8, 17),
            'size': (3, 1.2),
            'color': '#E8F5E8',
            'text': 'InputNode',
            'details': '• Validate user input\n• Initialize state object\n• Prepare for processing'
        },
        {
            'name': 'CheckContextNode',
            'pos': (8, 15),
            'size': (3, 1.2),
            'color': '#E8F0FF',
            'text': 'CheckContextNode',
            'details': '• GET /get_context from MCP\n• Retrieve conversation history\n• Get token counts & summaries'
        },
        {
            'name': 'ToolDecisionNode',
            'pos': (8, 13),
            'size': (3, 1.2),
            'color': '#FFF8E8',
            'text': 'ToolDecisionNode',
            'details': '• Check for factual keywords\n• Pattern matching (regex)\n• Set should_use_tool flag'
        },
        {
            'name': 'Decision',
            'pos': (8, 11),
            'size': (2, 1),
            'color': '#FFFF99',
            'text': 'Tool Needed?',
            'details': 'Keywords: "what are", "types of",\n"genres", "information about"'
        },
        {
            'name': 'ToolCallNode',
            'pos': (4, 9),
            'size': (3, 1.2),
            'color': '#FFE8E8',
            'text': 'ToolCallNode',
            'details': '• POST /tool_call to MCP\n• Search knowledge base\n• Fallback to Wikipedia\n• Store results in state'
        },
        {
            'name': 'PromptAssemblyNode',
            'pos': (8, 7),
            'size': (3, 1.2),
            'color': '#F0E8FF',
            'text': 'PromptAssemblyNode',
            'details': '• Build system prompt (Adam persona)\n• Add conversation context\n• Include tool results if any\n• Ensure token limits'
        },
        {
            'name': 'LLMNode',
            'pos': (8, 5),
            'size': (3, 1.2),
            'color': '#E8FFE8',
            'text': 'LLMNode',
            'details': '• Send to OpenAI GPT-4\n• Apply temperature & limits\n• Handle API errors\n• Return character response'
        },
        {
            'name': 'OutputNode',
            'pos': (8, 3),
            'size': (3, 1.2),
            'color': '#E8F8FF',
            'text': 'OutputNode',
            'details': '• POST /add_message (user)\n• POST /add_message (assistant)\n• Update conversation stats\n• Return response'
        },
        {
            'name': 'END',
            'pos': (8, 1),
            'size': (1.5, 0.8),
            'color': '#FFB6C1',
            'text': 'Adam\'s\nResponse',
            'details': 'Wise, contextual response\nwith integrated knowledge'
        }
    ]
    
    # Draw boxes and text
    for step in steps:
        x, y = step['pos']
        w, h = step['size']
        
        # Main box
        rect = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.05",
            facecolor=step['color'],
            edgecolor='#333333',
            linewidth=2
        )
        ax.add_patch(rect)
        
        # Main text
        ax.text(x, y + 0.15, step['text'], 
               ha='center', va='center', 
               fontsize=12, fontweight='bold')
        
        # Details text
        ax.text(x, y - 0.2, step['details'], 
               ha='center', va='center', 
               fontsize=9, style='italic')
    
    # Draw arrows
    arrows = [
        (8, 18.2, 8, 17.8),  # START to InputNode
        (8, 16.4, 8, 15.8),  # InputNode to CheckContextNode
        (8, 14.4, 8, 13.8),  # CheckContextNode to ToolDecisionNode
        (8, 12.4, 8, 11.8),  # ToolDecisionNode to Decision
        (7, 10.5, 5.5, 9.8),  # Decision to ToolCallNode (YES)
        (8, 10.2, 8, 7.8),    # Decision to PromptAssemblyNode (NO)
        (5.5, 8.4, 6.5, 7.8), # ToolCallNode to PromptAssemblyNode
        (8, 6.4, 8, 5.8),     # PromptAssemblyNode to LLMNode
        (8, 4.4, 8, 3.8),     # LLMNode to OutputNode
        (8, 2.4, 8, 1.8),     # OutputNode to END
    ]
    
    for x1, y1, x2, y2 in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
    
    # Add YES/NO labels
    ax.text(5.5, 10.5, 'YES', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='red',
           bbox=dict(boxstyle="round,pad=0.2", facecolor='white', edgecolor='red'))
    
    ax.text(9.5, 9, 'NO', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='green',
           bbox=dict(boxstyle="round,pad=0.2", facecolor='white', edgecolor='green'))
    
    # Add side panels with additional information
    
    # State Object Evolution
    state_box = FancyBboxPatch(
        (0.5, 12), 2.5, 6,
        boxstyle="round,pad=0.1",
        facecolor='#F0F0F0',
        edgecolor='#666666',
        linewidth=1
    )
    ax.add_patch(state_box)
    
    ax.text(1.75, 17.5, 'State Object Evolution', 
           ha='center', va='center', fontsize=12, fontweight='bold')
    
    state_info = """Initial:
{
  "user_input": "...",
  "context": {},
  "should_use_tool": False,
  "tool_result": None,
  "prompt": "",
  "response": ""
}

After Context:
+ conversation history
+ token counts

After Decision:
+ should_use_tool: True/False
+ tool_query: "..."

After Tool (if needed):
+ tool_result: {...}

After Assembly:
+ complete prompt

Final:
+ Adam's response"""
    
    ax.text(1.75, 15, state_info, 
           ha='center', va='top', fontsize=8, 
           family='monospace')
    
    # MCP Server Interactions
    mcp_box = FancyBboxPatch(
        (13, 12), 2.5, 6,
        boxstyle="round,pad=0.1",
        facecolor='#F0F8FF',
        edgecolor='#4169E1',
        linewidth=1
    )
    ax.add_patch(mcp_box)
    
    ax.text(14.25, 17.5, 'MCP Server Calls', 
           ha='center', va='center', fontsize=12, fontweight='bold')
    
    mcp_info = """CheckContext:
GET /get_context
→ conversation history
→ token counts
→ summaries

ToolCall:
POST /tool_call
{"query": "..."}
→ knowledge base search
→ Wikipedia fallback

Output:
POST /add_message
{"role": "user", "content": "..."}
POST /add_message  
{"role": "assistant", "content": "..."}
→ conversation updated"""
    
    ax.text(14.25, 15, mcp_info, 
           ha='center', va='top', fontsize=8)
    
    # Add title
    ax.set_title('Adam NPC LangGraph Workflow - Detailed Flow Chart\nWith State Management and MCP Integration', 
                fontsize=16, fontweight='bold', pad=20)
    
    # Set axis properties
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 20)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ax.text(8, 0.3, f"Generated: {timestamp}", ha='center', va='center', 
           fontsize=10, style='italic', alpha=0.7)
    
    plt.tight_layout()
    return fig

def create_tool_decision_logic_diagram():
    """Create a diagram showing the tool decision logic."""
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Draw the decision tree
    ax.text(7, 9, 'Tool Decision Logic', ha='center', va='center', 
           fontsize=16, fontweight='bold')
    
    # Input box
    input_box = FancyBboxPatch(
        (6, 8), 2, 0.8,
        boxstyle="round,pad=0.05",
        facecolor='#E8F5E8',
        edgecolor='#333333',
        linewidth=2
    )
    ax.add_patch(input_box)
    ax.text(7, 8.4, 'User Input', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(7, 8, '"What are gaming genres?"', ha='center', va='center', fontsize=10, style='italic')
    
    # Keyword check
    keyword_box = FancyBboxPatch(
        (2, 6.5), 3, 1,
        boxstyle="round,pad=0.05",
        facecolor='#FFF8E8',
        edgecolor='#333333',
        linewidth=2
    )
    ax.add_patch(keyword_box)
    ax.text(3.5, 7.2, 'Keyword Check', ha='center', va='center', fontsize=12, fontweight='bold')
    keywords = '"what are", "what is", "types of",\n"genres", "information about"'
    ax.text(3.5, 6.7, keywords, ha='center', va='center', fontsize=9)
    
    # Regex check  
    regex_box = FancyBboxPatch(
        (9, 6.5), 3, 1,
        boxstyle="round,pad=0.05",
        facecolor='#FFE8E8',
        edgecolor='#333333',
        linewidth=2
    )
    ax.add_patch(regex_box)
    ax.text(10.5, 7.2, 'Regex Patterns', ha='center', va='center', fontsize=12, fontweight='bold')
    patterns = 'r"what.*genres.*"\nr"types.*of.*"\nr"information.*about.*"'
    ax.text(10.5, 6.7, patterns, ha='center', va='center', fontsize=9, family='monospace')
    
    # Decision diamond
    decision_points = np.array([[7, 5], [8, 4], [7, 3], [6, 4]])
    decision_patch = patches.Polygon(decision_points, closed=True, 
                                   facecolor='#FFFF99', edgecolor='#333333', linewidth=2)
    ax.add_patch(decision_patch)
    ax.text(7, 4, 'Any\nMatch?', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Results
    yes_box = FancyBboxPatch(
        (4, 1.5), 2.5, 1,
        boxstyle="round,pad=0.05",
        facecolor='#90EE90',
        edgecolor='#333333',
        linewidth=2
    )
    ax.add_patch(yes_box)
    ax.text(5.25, 2.2, 'should_use_tool = True', ha='center', va='center', fontsize=11, fontweight='bold')
    ax.text(5.25, 1.8, 'Route to ToolCallNode', ha='center', va='center', fontsize=9)
    
    no_box = FancyBboxPatch(
        (7.5, 1.5), 2.5, 1,
        boxstyle="round,pad=0.05",
        facecolor='#FFB6C1',
        edgecolor='#333333',
        linewidth=2
    )
    ax.add_patch(no_box)
    ax.text(8.75, 2.2, 'should_use_tool = False', ha='center', va='center', fontsize=11, fontweight='bold')
    ax.text(8.75, 1.8, 'Skip to PromptAssembly', ha='center', va='center', fontsize=9)
    
    # Draw arrows
    arrows = [
        (7, 7.6, 3.5, 7.2),     # Input to Keyword
        (7, 7.6, 10.5, 7.2),   # Input to Regex
        (3.5, 6.2, 6.5, 4.5),  # Keyword to Decision
        (10.5, 6.2, 7.5, 4.5), # Regex to Decision
        (6.5, 3.5, 5.7, 2.8),  # Decision to Yes
        (7.5, 3.5, 8.3, 2.8),  # Decision to No
    ]
    
    for x1, y1, x2, y2 in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, color='#333333'))
    
    # Add YES/NO labels
    ax.text(5.8, 3, 'YES', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='green')
    ax.text(8.2, 3, 'NO', ha='center', va='center', 
           fontsize=10, fontweight='bold', color='red')
    
    # Example analysis box
    example_box = FancyBboxPatch(
        (0.5, 0.2), 13, 1,
        boxstyle="round,pad=0.05",
        facecolor='#F0F0F0',
        edgecolor='#666666',
        linewidth=1
    )
    ax.add_patch(example_box)
    
    example_text = 'Example: "What are gaming genres?" → Contains "what are" (keyword) + "genres" (keyword) → should_use_tool = True'
    ax.text(7, 0.7, example_text, ha='center', va='center', fontsize=11, fontweight='bold', color='#006400')
    
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    
    plt.tight_layout()
    return fig

def main():
    """Generate all visualizations and save them."""
    
    print("🎨 Generating Adam NPC LangGraph Workflow Visualizations...")
    
    # Create output directory if it doesn't exist
    import os
    os.makedirs('visualizations', exist_ok=True)
    
    # Generate network diagram
    print("📊 Creating network workflow diagram...")
    fig1 = create_workflow_network_diagram()
    fig1.savefig('visualizations/langgraph_network_diagram.png', 
                dpi=300, bbox_inches='tight', facecolor='white')
    fig1.savefig('visualizations/langgraph_network_diagram.pdf', 
                bbox_inches='tight', facecolor='white')
    print("✅ Saved: langgraph_network_diagram.png/pdf")
    
    # Generate detailed flow chart
    print("📈 Creating detailed flow chart...")
    fig2 = create_detailed_flow_chart()
    fig2.savefig('visualizations/langgraph_detailed_flowchart.png', 
                dpi=300, bbox_inches='tight', facecolor='white')
    fig2.savefig('visualizations/langgraph_detailed_flowchart.pdf', 
                bbox_inches='tight', facecolor='white')
    print("✅ Saved: langgraph_detailed_flowchart.png/pdf")
    
    # Generate tool decision logic
    print("🔍 Creating tool decision logic diagram...")
    fig3 = create_tool_decision_logic_diagram()
    fig3.savefig('visualizations/tool_decision_logic.png', 
                dpi=300, bbox_inches='tight', facecolor='white')
    fig3.savefig('visualizations/tool_decision_logic.pdf', 
                bbox_inches='tight', facecolor='white')
    print("✅ Saved: tool_decision_logic.png/pdf")
    
    print("\n🎉 All visualizations generated successfully!")
    print("📁 Files saved in './visualizations/' directory:")
    print("   • langgraph_network_diagram.png/pdf")
    print("   • langgraph_detailed_flowchart.png/pdf") 
    print("   • tool_decision_logic.png/pdf")
    
    # Show the plots
    plt.show()

if __name__ == "__main__":
    main()
