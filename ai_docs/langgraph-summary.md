# LangGraph Documentation Summary

## Overview
LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain's capabilities to create agent and multi-agent workflows with key benefits in cycles, controllability, and persistence.

## Core Concepts

### 1. State Handling
- State is defined using TypedDict with optional Annotated types
- Reducers specify how to apply updates to state
- State keys without annotation are overwritten by updates
- Annotated state keys can use custom update logic (e.g., append vs. overwrite)

### 2. Graph Structure
- Built using StateGraph object
- Nodes represent units of work (functions/computations)
- Edges define transitions between nodes
- Supports conditional routing with edge functions
- START and END nodes mark entry/exit points

### 3. Checkpointing
- Enables persistent state across calls
- Supports memory management and state recovery
- Available checkpointers:
  - MemorySaver (in-memory storage)
  - SqliteSaver (local database)
  - PostgresSaver (production database)

### 4. Key Features

#### Tool Integration
```python
# Example of tool definition
tools = [TavilySearchResults(max_results=2)]
llm_with_tools = llm.bind_tools(tools)
```

#### Human-in-the-Loop
- Interrupt points can be defined using `interrupt_before` or `interrupt_after`
- Manual state updates via `update_state`
- Supports review and modification of agent actions

#### Time Travel
- Access previous states via `get_state_history`
- Resume from any checkpoint using checkpoint IDs
- Enables exploration of alternative paths

## Common Patterns

### 1. Basic Chatbot Setup
```python
class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
```

### 2. Tool Usage
```python
graph_builder.add_node("tools", ToolNode(tools=[tool]))
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
```

### 3. Human Oversight
```python
graph = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["tools"]
)
```

## Best Practices

1. State Management
   - Use appropriate reducers for state updates
   - Consider state persistence requirements
   - Handle state conflicts appropriately

2. Graph Design
   - Keep nodes focused on single responsibilities
   - Use conditional edges for complex routing
   - Consider error handling and recovery paths

3. Tool Integration
   - Validate tool outputs
   - Handle tool errors gracefully
   - Consider rate limits and API constraints

4. Human Integration
   - Clear interrupt points
   - Meaningful state inspection
   - Proper error handling

## Advanced Features

### 1. Custom State Updates
```python
graph.update_state(
    config,
    {"messages": new_messages},
    as_node="chatbot"
)
```

### 2. State History
```python
# Access previous states
for state in graph.get_state_history(config):
    print(state.values, state.next)
```

### 3. Checkpoint Management
```python
snapshot = graph.get_state(config)
# Resume from checkpoint
events = graph.stream(None, snapshot.config)
```

## Common Use Cases

1. Autonomous Agents
   - Research assistants
   - Task automation
   - Decision-making systems

2. Multi-Agent Systems
   - Collaborative workflows
   - Specialized agent teams
   - Complex task orchestration

3. Interactive Applications
   - Chat interfaces
   - Decision support systems
   - Human-AI collaboration tools

## Debugging Tips

1. Use `get_state` to inspect current state
2. Check `get_state_history` for execution path
3. Use LangSmith for tracing and monitoring
4. Test interrupts and state updates carefully

## Additional Resources

1. LangChain Documentation
2. LangSmith Integration
3. Graph Visualization Tools
4. Community Examples and Templates
