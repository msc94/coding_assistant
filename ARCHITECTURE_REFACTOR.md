# Agent Architecture Refactoring

## Problems with Original Architecture

### 1. Circular Dependencies
- `tools.py` imports from `logic.py` 
- Tools create agents that depend on logic
- Complex interdependencies make testing difficult

### 2. Tight Coupling
- Agent class serves as both data container and execution context
- Tools directly mutate agent state (`agent.output = ...`)
- Logic requires specific tools to be present

### 3. Confusing Responsibilities  
- `logic.py` contains both execution engine AND tool abstractions
- `tools.py` contains tools BUT also agent orchestration logic
- No clear separation between agent lifecycle and business logic

### 4. State Management Issues
- Agent state modified through side effects
- Tools like `FinishTaskTool` need direct agent reference
- Communication happens via shared mutable objects

## New Refactored Architecture

### Core Modules

#### 1. `agent.py` - Pure Data Structures
```python
@dataclass
class Agent:
    # Immutable configuration
    name: str
    model: str
    description: str
    parameters: List[Parameter]
    feedback_function: Callable
    
    # Mutable state with controlled access
    history: list = field(default_factory=list)
    output: AgentOutput | None = None
    
    # Clean methods for state management
    def set_output(self, result: str, summary: str, feedback: str = None)
    def reset_output(self)
    def create_start_message(self) -> str
```

#### 2. `engine.py` - Pure Execution Logic
```python
class AgentEngine:
    """Handles agent execution without knowing about specific tools"""
    
    def __init__(self, execution_context: AgentExecutionContext)
    
    async def execute_single_step(self, agent: Agent, callbacks, tokens)
    async def run_agent(self, agent: Agent, callbacks, tokens) -> AgentOutput
```

#### 3. `registry.py` - Tool Management
```python  
class ToolRegistry:
    """Centralized tool registration and execution"""
    
    def register_tool(self, tool: Tool)
    def register_tool_factory(self, name: str, factory: Callable)
    async def execute_tool(self, name: str, parameters: dict) -> str
    def get_tool_definitions(self) -> List[dict]
```

#### 4. `orchestration.py` - High-Level Coordination
```python
class AgentOrchestrator:
    """Coordinates agent creation and execution"""
    
    async def create_orchestrator_agent(self, task, summaries, instructions)
    async def create_research_agent(self, task, expected_output, expert=False)  
    async def run_agent(self, agent: Agent) -> AgentOutput
```

#### 5. `tools.py` - Clean Tool Implementations
```python
class FinishTaskTool(Tool):
    """No longer directly mutates agent - uses clean interface"""
    
    def __init__(self, agent: Agent):
        self._agent = agent
    
    async def execute(self, parameters: dict) -> str:
        self._agent.set_output(
            result=parameters["result"],
            summary=parameters["summary"],
            feedback=parameters.get("feedback"),
        )
        return "Agent output set."
```

### Key Architectural Improvements

#### ✅ Dependency Injection
- Tools registry injected into execution engine
- No more circular imports between modules
- Clear dependency flow: orchestration → engine → registry → tools

#### ✅ Separation of Concerns
- **Agent**: Pure data structure with controlled state mutations
- **Engine**: Pure execution logic, no business logic
- **Registry**: Tool management and discovery
- **Orchestration**: High-level agent coordination
- **Tools**: Business logic implementations

#### ✅ Immutable Agent Configuration
- Agent configuration (name, model, description) is immutable
- State changes happen through controlled methods
- No direct field manipulation

#### ✅ Event-Driven Communication
- Tools don't create other agents directly
- Orchestrator handles all agent lifecycle
- Clean callback system for monitoring

#### ✅ Testability
- Each component can be tested in isolation
- Mock dependencies easily injectable
- No hidden global state

### Migration Path

The refactored architecture maintains backward compatibility through:

1. **Compatibility Layer**: `OrchestratorToolCompat` provides the same interface as the original `OrchestratorTool`

2. **Progressive Migration**: Can migrate one component at a time

3. **Preserved Functionality**: All existing features work the same from the user perspective

### Usage Example

```python
# Create orchestrator
orchestrator = AgentOrchestrator(
    config=config,
    mcp_servers=mcp_servers,
    agent_callbacks=RichCallbacks(),
)

# Create and run agent
agent = await orchestrator.create_orchestrator_agent(
    task="Refactor this codebase",
    instructions="Use modern Python patterns"
)

result = await orchestrator.run_agent(agent)
```

### Benefits Summary

1. **Maintainability**: Clear module boundaries and responsibilities
2. **Testability**: Each component can be unit tested independently  
3. **Extensibility**: Easy to add new tools and agent types
4. **Debugging**: Clear execution flow and state management
5. **Performance**: Reduced overhead from circular dependencies
6. **Code Quality**: Eliminates complex interdependencies and side effects

The new architecture transforms a tightly-coupled system with unclear responsibilities into a clean, modular design that's much easier to understand, test, and extend.
