"""
LangGraph Agent for MPC Image Search
Demonstrates: LLM → Tool → Response flow
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import operator
import os


# Define agent state
class AgentState(TypedDict):
    """State passed between nodes"""
    messages: Annotated[list, operator.add]
    user_query: str
    tool_results: dict


# Initialize LLM
def get_llm():
    """Get Groq LLM instance"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    
    return ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=0,
        api_key=api_key
    )


# Parse query node
def parse_query_node(state: AgentState) -> AgentState:
    """
    Parse user query to extract location, dates, etc.
    """
    print(f"\n🔍 Parsing query: {state['user_query']}")
    
    llm = get_llm()
    
    # Prompt to extract parameters
    system_prompt = """You are a geospatial query parser. Extract search parameters from user queries.

Extract:
- location: Place name
- collection: satellite type (sentinel-2, landsat, hls)
- start_date: YYYY-MM-DD format
- end_date: YYYY-MM-DD format
- max_cloud_cover: percentage (default 20)

Examples:
"Sentinel-2 images of Lahore in August 2024 with low clouds"
→ location: Lahore
→ collection: sentinel-2
→ start_date: 2024-08-01
→ end_date: 2024-08-31
→ max_cloud_cover: 20

If dates not specified, use current month.
"""
    
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state['user_query']}
    ])
    
    print(f"✅ Parsed: {response.content}")
    
    state['messages'].append(AIMessage(content=response.content))
    return state


# Tool execution node
def tool_node(state: AgentState) -> AgentState:
    """
    Execute MPC search tool
    """
    print(f"\n🛠️ Executing MPC search tool")
    
    # This would be replaced with actual tool execution
    # For now, we'll simulate
    from app.llm.tools.mpc_search_tool import search_mpc_images, geocode_to_bbox
    
    # Example: hardcoded for testing
    bbox = geocode_to_bbox("lahore")
    
    result = search_mpc_images.invoke({
        "location_name": "Lahore, Pakistan",
        "bbox": bbox,
        "collection": "sentinel-2-l2a",
        "start_date": "2024-08-01",
        "end_date": "2024-08-31",
        "max_cloud_cover": 20,
        "limit": 5
    })
    
    state['tool_results'] = result
    state['messages'].append(ToolMessage(
        content=str(result),
        tool_call_id="mpc_search"
    ))
    
    print(f"✅ Tool returned: {result['images_found']} images")
    return state


# Generate response node
def generate_response_node(state: AgentState) -> AgentState:
    """
    Generate natural language response from tool results
    """
    print(f"\n💬 Generating response")
    
    llm = get_llm()
    
    tool_results = state['tool_results']
    
    # Create prompt for LLM
    prompt = f"""Based on the MPC search results, create a concise natural language response.

User Query: {state['user_query']}

Search Results:
- Location: {tool_results.get('location')}
- Collection: {tool_results.get('collection')}
- Images Found: {tool_results.get('images_found')}

Generate a helpful response summarizing the findings. If images were found, mention key details like dates and cloud cover.
"""
    
    response = llm.invoke([{"role": "user", "content": prompt}])
    
    state['messages'].append(AIMessage(content=response.content))
    
    print(f"✅ Response: {response.content[:100]}...")
    return state


# Build the graph
def create_mpc_agent():
    """Create LangGraph workflow for MPC search"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_query", parse_query_node)
    workflow.add_node("execute_tool", tool_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # Add edges
    workflow.set_entry_point("parse_query")
    workflow.add_edge("parse_query", "execute_tool")
    workflow.add_edge("execute_tool", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Compile
    app = workflow.compile()
    
    return app


# Test function
async def test_agent():
    """Test the MPC agent"""
    
    print("\n" + "="*60)
    print("🤖 TESTING LANGGRAPH MPC AGENT")
    print("="*60)
    
    agent = create_mpc_agent()
    
    # Test query
    test_query = "Find Sentinel-2 images of Lahore from August 2024 with less than 20% cloud cover"
    
    initial_state = {
        "messages": [HumanMessage(content=test_query)],
        "user_query": test_query,
        "tool_results": {}
    }
    
    # Run agent
    print(f"\n📝 User Query: {test_query}")
    
    result = await agent.ainvoke(initial_state)
    
    # Print final response
    print("\n" + "="*60)
    print("🎯 FINAL RESPONSE")
    print("="*60)
    
    final_message = result['messages'][-1]
    print(f"\n{final_message.content}\n")
    
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())