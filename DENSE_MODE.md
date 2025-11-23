# Dense Mode

Dense mode (`--dense`) provides a compact, minimal output format for the coding assistant.

## Usage

```bash
coding-assistant --dense
```

Or combined with other options:

```bash
coding-assistant --dense --chat-mode
```

## Features

### Minimal Formatting
- ✅ No panels - just plain text
- ✅ Unicode markers instead of boxes (▸, ◂, ◉, 💭)
- ✅ Compact tool call output
- ✅ Chunks always printed (no flag needed)
- ✅ Reasoning printed with 💭 marker

### Tool Call Output
Instead of verbose panels, tool calls show:
- Tool name and parameters
- Number of lines in results (not full output)

Example:
```
▸ mcp_coding_assistant_mcp_shell_execute({"command": "ls -la"})
  → 45 lines
```

### Agent Messages
```
▸ Agent Orchestrator (gpt-5) starting
◉ User: What files are in this directory?
◉ Assistant: I'll check the directory for you.
◂ Agent Orchestrator complete
```

## Comparison

| Feature | Default Mode | Dense Mode |
|---------|--------------|------------|
| Panels | ✅ Rich panels | ❌ Plain text |
| Tool results | Full output | Line count only |
| Chunks | Optional (--print-chunks) | Always on |
| Reasoning | Optional (--print-reasoning) | Always on |
| Markers | Panel borders | Unicode (▸ ◂ ◉ 💭) |
| Scrollback | Works | Works |

## When to Use Dense Mode

Use dense mode when:
- You want minimal visual clutter
- You're working in a narrow terminal
- You prefer to see more content on screen
- You want faster scrolling through output
- You're familiar with the tool and don't need visual structure

Use default mode when:
- You want clear visual separation
- You're new to the tool
- You need to see full tool results
- You want pretty formatting

## Implementation

Dense mode uses `DenseProgressCallbacks` which:
- Prints text directly without Rich panels
- Formats tool calls compactly
- Truncates long arguments (shows `<N chars>` instead)
- Counts result lines instead of showing full output
- Always enables chunks
- Shows reasoning with 💭 marker

## Example Output

```
▸ Agent Orchestrator (gpt-5) starting
◉ User: Create a Python script to calculate fibonacci numbers
💭 I need to create a Python file with fibonacci implementation
◉ Assistant: I'll create a fibonacci calculator script.
▸ mcp_coding_assistant_mcp_filesystem_write({"path": "fibonacci.py", "content": "<143 chars>"})
  → 1 lines
◉ Assistant: I've created fibonacci.py with the implementation.
◂ Agent Orchestrator complete
Summary: Created a Python script that calculates Fibonacci numbers
```
