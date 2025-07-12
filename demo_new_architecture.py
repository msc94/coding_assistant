"""Demo script showing the new agent architecture in action."""

import asyncio
import logging
from pathlib import Path

from coding_assistant.agents.orchestration import AgentOrchestrator
from coding_assistant.agents.callbacks import RichCallbacks
from coding_assistant.config import Config, MCPServerConfig

logging.basicConfig(level=logging.INFO)


async def demo_new_architecture():
    """Demonstrate the new agent architecture."""
    
    # Create configuration
    config = Config(
        model="gpt-4o",
        expert_model="gpt-4o",
        enable_feedback_agent=False,
        enable_user_feedback=False,
        instructions=None,
        sandbox_directories=[Path("/tmp")],
        mcp_servers=[],
    )
    
    # Create agent callbacks for output
    callbacks = RichCallbacks()
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(
        config=config,
        mcp_servers=[],  # No MCP servers for this demo
        agent_callbacks=callbacks,
    )
    
    print("🚀 Creating orchestrator agent...")
    
    # Create orchestrator agent
    orchestrator_agent = await orchestrator.create_orchestrator_agent(
        task="Say 'Hello World' and explain the new agent architecture",
        instructions="Be concise and helpful",
    )
    
    print("▶️  Running orchestrator agent...")
    
    # Run agent
    try:
        result = await orchestrator.run_agent(orchestrator_agent)
        print(f"\n✅ Result: {result.result}")
        print(f"📝 Summary: {result.summary}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🏗️  Architecture Benefits:")
    print("✅ Clean separation between agent data and execution logic")
    print("✅ Tool registry system eliminates circular dependencies")
    print("✅ Agent state management through immutable updates")
    print("✅ Orchestrator handles agent coordination")
    print("✅ No more tools directly creating other agents")


if __name__ == "__main__":
    asyncio.run(demo_new_architecture())
