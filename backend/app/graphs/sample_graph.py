from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, START, END

# ==========================================
# 1. State Model
# ==========================================
class AgentState(TypedDict):
    """
    The State represents the data structure that is passed between nodes.
    Each node in the graph receives this state, can perform actions, and
    returns updates to this state.
    
    Using Annotated with operator.add means that when a node returns new
    messages, they are appended to the existing list rather than overwriting it.
    """
    messages: Annotated[Sequence[str], operator.add]
    # We can add more fields here like 'current_status', 'plan', etc.

# ==========================================
# 2. Sample Node
# ==========================================
def sample_node(state: AgentState):
    """
    A Node is a Python function that takes the current State as input,
    performs some logic (like calling an LLM or an API), and returns
    a dictionary representing updates to the State.
    """
    # Simply appending a sample message to the state
    return {"messages": ["Hello from the sample node!"]}

# ==========================================
# 3. Graph Definition & Edges
# ==========================================
# We initialize the StateGraph with our State model
workflow = StateGraph(AgentState)

# We add nodes to the graph. 
# The first argument is the node's name, the second is the function it calls.
workflow.add_node("sample_node", sample_node)

# Edges define the flow of execution.
# START is a special node that indicates where the graph begins.
# We add an edge from START to our sample_node.
workflow.add_edge(START, "sample_node")

# We add an edge from our sample_node to END.
# END is a special node indicating that graph execution is finished.
workflow.add_edge("sample_node", END)

# ==========================================
# 4. Graph Compilation (Execution)
# ==========================================
# Compiling the graph turns it into an executable runnable (like a LangChain Runnable).
# This is what we will actually invoke in our API or agents.
graph = workflow.compile()

# Example of how it would be invoked (commented out):
# initial_state = {"messages": ["Initial message"]}
# result = graph.invoke(initial_state)
