# Coding Assistant

## 🤖 Project Title: Coding Assistant

---

## Introduction

**Coding Assistant** is an advanced Python-based tool that leverages agent-based automation to streamline, support, and automate various coding tasks. It deploys multi-agent orchestration, research, automated development, feedback validation, and Model Context Protocol (MCP) tool integrations to tackle complex software engineering workflows efficiently and reliably. With agent roles specialized for distinct phases of software work, Coding Assistant optimizes developer productivity in real-world codebases.

---

## Key Features

- **Agent Orchestration**: The Orchestrator agent coordinates tasks by delegating work to specialized sub-agents as required.
- **Research Agent**: Conducts automated research to answer questions or gather required info.
- **Developer Agent**: Implements code based strictly on provided, well-defined implementation plans.
- **Feedback Agent**: Automatically reviews and validates agent results, ensuring they meet user requirements.
- **Flexible CLI**: Launch, control, and interact with agents/tasks from the command line.
- **MCP Server Integration**: Native support for MCP server toolchains (filesystem, fetch/web search, git, Tavily, etc). 
- **Tracing with OpenTelemetry**: Optional tracing and observability via OpenTelemetry compatible endpoints.
- **Sandbox Security**: Landlock-based filesystem sandbox for secure task execution.

---

## Software Architecture

The Coding Assistant is structured as a multi-agent system coordinated via an Orchestrator. The user provides configuration, CLI inputs, or explicit tasks, which flow into the Orchestrator. The Orchestrator directs requests to specialized agent roles (Research Agent, Developer Agent, Feedback Agent), each leveraging MCP server tools for file access, shell commands, git, web search/fetch, and more. All task results are returned to the user through the CLI. The architecture below is depicted in a Mermaid diagram for clarity.

```mermaid
flowchart TD
    subgraph User_Group
        User_Node[User]
    end
    subgraph CLI_Group
        CLI_Node[CLI / Terminal]
    end

    subgraph Orchestrator_Group
        ORCH_Node[Orchestrator Agent]
    end

    subgraph Agents_Group
        RA_Node[Research Agent]
        DA_Node[Developer Agent]
        FA_Node[Feedback Agent]
    end

    subgraph MCP_Servers_Group [MCP Servers / Tooling]
        FS_Node[Filesystem]
        GIT_Node[Git]
        SH_Node[Shell]
        WEB_Node[Fetch / Tavily]
    end

    User_Node -->|"Inputs via"| CLI_Node
    CLI_Node -->|"Config / Task / Command"| ORCH_Node

    ORCH_Node -->|"Coordinates"| RA_Node
    ORCH_Node -->|"Delegates"| DA_Node
    ORCH_Node -->|"Sends for review"| FA_Node

    RA_Node -- "Uses tools" --> FS_Node
    RA_Node -- "Uses tools" --> GIT_Node
    RA_Node -- "Uses" --> WEB_Node

    DA_Node -- "Uses tools" --> FS_Node
    DA_Node -- "Uses tools" --> GIT_Node
    DA_Node -- "Uses tools" --> SH_Node
    DA_Node -- "Uses" --> WEB_Node

    FA_Node -- "Uses tools" --> FS_Node
    FA_Node -- "Uses tools" --> GIT_Node

    FS_Node -.->|"Provides Services"| MCP_Servers_Group
    GIT_Node -.->|"Provides Services"| MCP_Servers_Group
    SH_Node -.->|"Provides Services"| MCP_Servers_Group
    WEB_Node -.->|"Provides Services"| MCP_Servers_Group

    ORCH_Node -->|"Results / Outputs"| CLI_Node
```


**Explanation:**
- **User interacts with the Coding Assistant through the CLI.**
- **CLI collects user inputs and passes them to the Orchestrator Agent.**
- **The Orchestrator delegates tasks to specialist agents (Research, Developer, Feedback).**
- **Agents interact with external services (MCP Servers: Filesystem, Git, Shell, Fetch/Tavily) as needed for their task.**
- **Results flow back through the Orchestrator to the CLI, and are shown to the user.**

---

## Installation Guide

### System Requirements
- **Python**: 3.12+ (see `.python-version`)
- **Node.js**: For running some MCP servers (fetch/filesystem).
- **Additional tools**: `uv`, `npx`, and optionally `git`, `npm`, `pytest`.

### 1. Clone the repository & enter the directory
```bash
git clone <REPO_URL>
cd coding_assistant
```

### 2. Set up a virtual environment
```bash
uv venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
uv pip install -r requirements.txt  # Or use 'uv pip install .' if project configuration allows
```
*Alternatively (recommended for dev):*
```bash
uv pip install -e .
```

### 4. Set environment variables
- Copy or edit `.envrc` to provide API keys:
    - `OPENAI_API_KEY` (for model access)
    - `TAVILY_API_KEY` (for web research)
    - `DEEPSEEK_API_KEY` (optional, if used)

If using direnv:
```bash
direnv allow
```

---

## Quickstart

### Launching the Orchestrator or Agents via CLI

#### Run an Orchestrator Task:
```bash
uv run coding-assistant --task "Refactor all function names to snake_case."
```

#### Print all available MCP tools:
```bash
uv run coding-assistant --print_mcp_tools
```

#### Example: Launch a Developer Agent directly (Python API):
See `src/coding_assistant/agents/agents.py` for agent API usage.

---

## Project Structure

```
coding_assistant/
├── src/
│   └── coding_assistant/
│       ├── __init__.py
│       ├── config.py            # Central config dataclass & helpers
│       ├── instructions.py      # Special agent instructions
│       ├── llm/
│       │   └── model.py         # LLM model interface
│       ├── main.py              # CLI entry point
│       ├── sandbox.py           # Sandbox implementation (Landlock)
│       ├── tools.py             # MCP server & tool integration
│       ├── agents/
│       │   ├── agents.py        # All core agent/tool classes
│       │   ├── logic.py         # Agent orchestration logic
│       │   └── tests/           # Agent-specific tests
│       └── tests/               # Sandbox & integration tests
├── justfile                     # Commands (e.g. test)
├── pyproject.toml               # Build/setup & dependency metadata
├── README.md                    # This document
...
```

- **pyproject.toml**: Declares dependencies, build configs, CLI entry point.
- **justfile**: Handy project/dev commands (e.g. test: `uv run pytest -n auto`).
- **.envrc**: Example env vars for API keys.

---

## Configuration

- Environment variables should be set for:
    - `OPENAI_API_KEY` (model providers i.e. OpenAI, DeepSeek)
    - `TAVILY_API_KEY` (enables web/Tavily research agent)
    - `DEEPSEEK_API_KEY` (if DeepSeek models are specifically used)
    - `CODING_ASSISTANT_MODEL`, `CODING_ASSISTANT_EXPERT_MODEL` (optional: default/override LLMs)
- Place these vars in `.envrc` or export manually in your shell.
- MCP servers and agent tools are dynamically initialized via `tools.py` and main config class (`Config`).

---

## Development

- **Style**: Uses [Black](https://black.readthedocs.io) (see pyproject.toml: line length 120)
- **Tests**: `pytest`, `pytest-asyncio`, `pytest-xdist` (see `justfile` for parallel run command)
    - Run tests: `just test` or `uv run pytest -n auto`
    - Test locations: `src/coding_assistant/agents/tests`, `src/coding_assistant/tests`
- **Type hints** and `dataclasses` are used throughout for clarity.
- Contributions welcome: open issues or PRs, ensure new tests are added if functionality changes.

---

## Advanced Usage

- **Tracing/Observability:**
    - OpenTelemetry is automatically initialized if an endpoint is found at `http://localhost:4318/v1/traces`.
    - Configure OpenTelemetry collector as needed for in-depth tracing.
- **Tavily integration:**
    - If `TAVILY_API_KEY` is set, the Tavily web research MCP server loads automatically.
- **Sandboxing:**
    - By default, filesystem access is restricted and safely isolated via Landlock and user directory rules. See `sandbox.py` for implementation.

---

## FAQ & Troubleshooting

### Common Issues
- **"No MCP servers found":** Ensure Node.js and Python dependencies are correctly installed.
- **API key errors:** Double-check `.envrc`, exported variables, and keys, especially for OpenAI/Tavily.
- **Sandbox errors:** If you see `PermissionError`, review allowed directories in your sandbox call or test.
- **Tracing not enabled:** Ensure an OpenTelemetry endpoint is running at the expected URL.
- **Python version mismatch:** Use Python 3.12 as required by `.python-version`.

### Getting Help
- Check the in-code docstrings for each agent, tool, or test for further examples.
- Open an issue or PR on GitHub.

---

## License and Credits

- **License:** MIT
- **Contributions:** PRs and issues are welcome. Please ensure to add tests for all new functionality.
