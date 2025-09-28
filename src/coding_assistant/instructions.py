from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imported only for type checking to avoid runtime dependency/cycles
    from coding_assistant.tools.mcp import MCPServer

INSTRUCTIONS = """
- Do not initialize a new git repository, unless your client explicitly requests it.
- Do not commit any changes to the git repository, unless your client explicitly requests it.
- Do not switch branches before asking the user.
- Do not run anything interactively, e.g. `git rebase -i`.
- When you have made a change to a project, ask the user if you should commit the changes.
- Do not install any software on the users computer before asking.
- Do not run any binary using `uvx` or `npx` without asking the user first.
- When the user asks a question, be *very* sure before starting a web search that this is what the user wants.
- If you output text, use markdown formatting where appropriate.
- Make use of sub-agents to reduce your context size.
    - If you expect to read lots of files to gather information, launch a sub-agent.
    - When possible, launch multiple sub-agents in parallel to speed up your work.
    - It is very important to pass all necessary context to the sub-agent, they do not have access to your conversation history with the client. The only thing they see is the parameters you pass to them.
    - You are responsible for the work of the sub-agents. Review it before showing it to the client.
""".strip()

PLANNING_INSTRUCTIONS = """
- You are in planning mode.
    - Create a plan for the task at hand in close collaboration with the client.
    - Do not implement the plan.
    - Do not make any filesystem changes, except for saving the plan.
    - Present pros and cons of different approaches to the client.
    - Ask the client for feedback on the plan.
    - Planning might take multiple iterations.
    - The default directory to save the plan to is .coding_assistant/plans in the current working directory.
    - Come up with a sensible filename for the plan.
    - Each plan should include a section with a detailed description of the problem and the implementation.
    - It should be clear why this implementation has been chosen over others.
    - Each plan should include a list of tasks that need to be completed to implement the plan.
    - Use a markdown task list for the tasks, such that the tasks can be checked off.
""".strip()


def get_instructions(
    working_directory: Path,
    plan: bool,
    user_instructions: list[str],
    mcp_servers: list["MCPServer"] | None = None,
) -> str:
    instructions = INSTRUCTIONS.strip()

    if plan:
        instructions = f"{instructions}\n{PLANNING_INSTRUCTIONS.strip()}"

    local_instructions_path = working_directory / ".coding_assistant" / "instructions.md"
    if local_instructions_path.exists():
        instructions = f"{instructions}\n{local_instructions_path.read_text().strip()}"

    agents_md_path = working_directory / "AGENTS.md"
    if agents_md_path.exists():
        instructions = f"{instructions}\n{agents_md_path.read_text().strip()}"

    for instruction in user_instructions:
        instructions = f"{instructions}\n{instruction.strip()}"

    # Append MCP server instructions (if provided)
    if mcp_servers:
        for s in mcp_servers:
            try:
                mi = getattr(s, "instructions", None)
            except Exception:
                mi = None
            if isinstance(mi, str) and mi.strip():
                instructions = f"{instructions}\n{mi.strip()}"

    return instructions
