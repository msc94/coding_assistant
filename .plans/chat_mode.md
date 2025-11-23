# Chat Mode: Design and Implementation Plan (Open‑Ended)

## Goal
Introduce an open‑ended “chat mode” for the root orchestrator agent: when the assistant sends a message without any tool calls, control transfers to the user. The session does not require a task, does not include a `finish_task` tool, and does not terminate via a tool — it continues until the user exits.

## Decisions (confirmed)
- Scope: chat mode applies only to the root agent; sub‑agents do not use chat mode.
- AskClientTool: disabled while chat mode is enabled.
- Prompt text: default to `Reply to {agent_name}:` (can be made configurable later).
- Start instructions: explicitly describe chat mode behavior (tools optional; control returns to user via assistant messages without tool calls; no `finish_task`).
- Default: chat mode enabled by default in the CLI.
- Mixed messages: if tool calls are present, execute tools immediately; do not prompt the user first.
- Prompt frequency: at most once per assistant step without tool calls.
- History: store user chat replies as plain `role=user` entries (no special tags).
- No task and no `finish_task` in chat mode (open‑ended session).
- Interrupts in chat mode: Ctrl‑C should immediately open the user chat prompt (not exit/confirm).

## Status
- [x] Config flag and CLI `--chat-mode` (default on)
- [x] Open‑ended chat loop (`run_chat_loop`) and session (`run_chat_session`)
- [x] Start message for chat mode
- [x] `handle_tool_calls` prompts user when no tool calls in chat mode
- [x] `do_single_step` skips `finish_task` requirement in chat mode
- [x] AskClient disabled in chat mode (omitted from chat tool list)
- [x] Tests for chat mode behaviors
- [x] CLI branch to chat session when enabled
- [ ] Shorten conversation behavior decision (open)

## Current Behavior Overview (impact points)
- `run_agent_loop`/`do_single_step` require presence of `finish_task` and rely on `state.output` set by `FinishTaskResult` to exit. In chat mode, we must not require `finish_task` and must not depend on `state.output` for termination.
- `handle_tool_calls` injects a correction when there are no tool calls. In chat mode, this should instead prompt the user and append a user message.
- CLI currently requires `--task`; chat mode should not require a task at all.
- Orchestrator setup (`OrchestratorTool`) builds tools including `finish_task` and expects a return value; chat mode should bypass or modify this.

Relevant file references
- Agent step/loop: src/coding_assistant/agents/execution.py:31, 186, 231, 295
- History append: src/coding_assistant/agents/history.py:4, 25, 36
- CLI: src/coding_assistant/main.py:180, 296
- Orchestrator/sub‑agent tools: src/coding_assistant/tools/tools.py:36, 129
- UI: src/coding_assistant/ui.py:11

## Proposed Behavior (Chat Mode)
- Start session with no required task and with a start message describing open‑ended chat mode.
- Assistant messages:
  - With tool calls: execute tools and append results; continue.
  - Without tool calls: prompt the user once for that step (`UI.ask("Reply to {agent_name}:")`), append as `role=user`, continue.
- Session lifetime: open‑ended; keep looping until the user exits. No `finish_task` and no `state.output` termination.
- Interrupts: pressing Ctrl‑C during a step should immediately trigger the same user chat prompt; append the reply and continue.

## Design Changes
1. Configuration & CLI
   - Add `enable_chat_mode: bool` to `Config`.
   - Add `--chat-mode/--no-chat-mode` (BooleanOptionalAction) default True.
   - Make `--task` optional: when chat mode is on, do not require it and do not construct a task parameter.
2. Chat Session Runner (new)
   - Implement `run_chat_session(...)` in `main.py` that:
     - Builds an `AgentDescription` for the root agent with tools: `ShortenConversation` + MCP tools (+ others), excluding `FinishTaskTool` and `AskClientTool`.
     - Builds an `AgentState` (resume history if provided).
     - Starts a new loop `run_chat_loop(...)` (see next item).
     - Saves history on exit (and trims like today). Skip conversation summary saving unless a summary is produced via `shorten_conversation`.
3. Chat Loop (new)
   - Implement `run_chat_loop(ctx, *, agent_callbacks, tool_callbacks, completer, ui, shorten_conversation_at_tokens, is_interruptible)`:
     - Start message: use a chat‑mode variant (see below).
     - Loop forever, calling `do_single_step` each iteration.
     - Do not check for `state.output` and do not call `on_agent_end`.
     - On interruption (SIGINT), immediately present the user chat prompt (same as assistant‑no‑tools case) and append the user message, then continue.
     - Keep the token‑based “shorten conversation” hint as today (open item below).
4. Start Message (chat‑mode variant)
   - Extend `_create_start_message` or add `_create_chat_start_message` that:
     - Removes “You must use at least one tool call in every step.”
     - Removes “Use the `finish_task` tool when you have fully finished your task.”
     - Adds: “You are in chat mode. You may converse without tools. When you do not know what to do next, reply without tool calls to return control to the user. Use tools only when they materially advance the work.”
   - In `run_chat_loop`, append this chat start message.
5. Tool‑call Handling (augment existing)
   - In `handle_tool_calls`:
     - If chat mode is disabled and `tool_calls` is empty: keep the corrective injection (unchanged behavior).
     - If chat mode is enabled and `tool_calls` is empty: prompt once via `UI.ask("Reply to {desc.name}:")`, append user message, and return.
6. Orchestrator/Sub‑agent Integration
   - In CLI `main._main`:
     - If `args.chat_mode`: call `run_chat_session` directly instead of `run_orchestrator_agent`.
     - Else: keep current `run_orchestrator_agent` path.
   - `AgentTool.execute` remains unchanged (sub‑agents are not in chat mode). Ensure it passes `enable_chat_mode=False`/omits chat loop.
7. Disable AskClient in Chat Mode
   - Do not include `AskClientTool` in the root agent’s tool list when chat mode is on.
8. Persistence
   - Reuse history save/trim on exit as done today.
   - Skip `save_conversation_summary` unless explicitly produced via `shorten_conversation` (no final `summary`).

## Implementation Steps
1. Add config flag and CLI wiring
   - Edit: `src/coding_assistant/config.py` add `enable_chat_mode: bool`.
   - Edit: `src/coding_assistant/main.py` (add `--chat-mode` default True; thread to `create_config_from_args`).
2. Thread flag to agent loops
   - Edit: `src/coding_assistant/agents/execution.py:run_agent_loop` (add `enable_chat_mode: bool` param; default True for callers in this repo’s CLI path).
   - Edit: `src/coding_assistant/tools/tools.py:OrchestratorTool.execute` (pass config flag) and `AgentTool.execute` (pass `False`).
3. Adjust start message
   - Edit: `src/coding_assistant/agents/execution.py:_create_start_message` (param or conditional string tweak when chat mode enabled) and adapt call site.
4. Implement chat mode in `handle_tool_calls`
   - Edit: `src/coding_assistant/agents/execution.py:handle_tool_calls` to prompt user when no tools and chat mode enabled, append user reply, then return.
5. Disable AskClient in orchestrator when chat mode enabled
   - Edit: `src/coding_assistant/tools/tools.py:OrchestratorTool.execute` tools list; omit `AskClientTool` or pass `enabled=False` based on `self._config.enable_chat_mode`.
6. Tests
   - Add `src/coding_assistant/agents/tests/test_chat_mode.py`:
     - `test_chat_mode_prompts_user_on_no_tool_calls` – root: prompt and append user reply.
     - `test_chat_mode_skips_prompt_when_tools_present` – tools execute, no prompt.
     - `test_chat_mode_does_not_modify_finish_task_flow` – completion can still end via `finish_task` without chat prompts.
     - `test_non_chat_mode_keeps_correction_behavior` – existing behavior preserved when flag is False.
     - `test_sub_agent_never_prompts_in_chat_mode` – ensure `AgentTool` run passes `enable_chat_mode=False`.
   - Update helper assertions if they depend on prompt text `Reply to {agent_name}:`.
7. Docs and CLI help
   - Add description for `--chat-mode` explaining behavior and that it only applies to the root agent.

## Edge Cases & Considerations
- Termination: In chat mode, session ends when the user terminates the process; we do not add explicit exit controls.
- Interrupt handling: In chat mode, SIGINT shows user chat prompt immediately; append reply and continue.
- Token growth: Keep “shorten conversation” hint as today, but it’s an open item whether to keep/adjust it.
- Resume: Resuming history in chat mode is supported; next assistant‑without‑tools step will prompt the user.

## Start Message (proposed content)
“You are in chat mode. You may converse without using tools. When you do not know what to do next, reply without any tool calls to return control to the user. Use tools only when they materially advance the work.”

## Open Item
- Shorten conversation in chat mode: keep available and hint as today, or suppress the hint? We can implement as today and revisit based on usage.

