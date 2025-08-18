# Test Gap Plan

This document lists the key remaining test gaps for the agents/execution layer (and closely related flows), with concrete tests to add. A Markdown task list is provided for easy tracking.


## High-priority gaps and tests to add

- [x] ShortenConversation flow resets history
  - Add: `src/coding_assistant/agents/tests/test_execution_shorten_conversation.py::test_shorten_conversation_resets_history`
  - Assert: invoking `shorten_conversation` appends tool result "Conversation shortened and history reset." and resets history to contain:
    - The fresh START_MESSAGE
    - The "A summary of your conversation …" user message
  - Verify subsequent steps continue from the new history.

- [x] Tool confirmation at handle_tool_call level (fast unit)
  - Add: `src/coding_assistant/agents/tests/test_execution.py::test_tool_confirmation_denied_and_allowed`
  - Setup: `tool_confirmation_patterns=[r"^execute_shell_command"]`, UI.confirm False/True.
  - Assert denial writes a tool message "Tool execution denied." and does not run the tool; positive path runs it.

- [x] Reasoning content handling
  - Add: `src/coding_assistant/agents/tests/test_model_contract.py::test_reasoning_is_forwarded_and_not_stored`
  - FakeCompleter returns a message with `reasoning_content`; assert `callbacks.on_assistant_reasoning` receives the content and reasoning is not stored in history.

- [x] do_single_step guard rails
  - Add:
    - `test_requires_finish_tool`
    - `test_requires_shorten_tool`
    - `test_requires_non_empty_history`
    - Location: `src/coding_assistant/agents/tests/test_model_contract.py`
  - Assert `RuntimeError` is raised in each missing precondition case.

- [x] Multiple tool calls handled in order within one step
  - Add: `src/coding_assistant/agents/tests/test_run_loop_slices.py::test_multiple_tool_calls_processed_in_order`
  - FakeCompleter returns one assistant message with two tool calls; assert both execute and history order is correct.

- [x] Interrupt flow inside run_agent_loop injects feedback and continues
  - Add: `src/coding_assistant/agents/tests/test_run_loop_slices.py::test_interrupt_feedback_injected_and_loop_continues`
  - Force `InterruptibleSection.was_interrupted=True` once; mock `UI.ask` to return feedback; assert FEEDBACK_TEMPLATE is appended and the loop continues to a final finish.

- [x] run_agent_loop rejects when agent.output already set
  - Add: `src/coding_assistant/agents/tests/test_run_loop_slices.py::test_errors_if_output_already_set`
  - Pre-set `agent.output`; assert `RuntimeError`.

- [x] enable_user_feedback=True with immediate "Ok"
  - Add: `src/coding_assistant/agents/tests/test_run_loop_slices.py::test_feedback_ok_does_not_reloop`
  - Ensure loop exits after first finish when `UI.ask` returns "Ok".

- [x] Start message includes MCP server instructions
  - Add: `src/coding_assistant/agents/tests/test_execution_start_message.py::test_start_message_includes_mcp_instructions`
  - Agent with a mocked MCP server that has instructions; assert the first user message includes the MCP instructions block.

## Additional improvements

- [x] Robustness on invalid `tool_call.function.arguments`
  - Implementation: Catch `json.JSONDecodeError` in `handle_tool_call` and append a tool message describing the parse error instead of raising.
  - Test: `src/coding_assistant/agents/tests/test_execution.py::test_invalid_tool_arguments_reported`

- [x] Unexpected tool result type
  - Add: `src/coding_assistant/agents/tests/test_execution.py::test_unknown_result_type_raises`
  - Create a fake tool returning an unsupported result type; assert `TypeError` from `handle_tool_call`.

- [x] Callback lifecycle assertions
  - Add: `src/coding_assistant/agents/tests/test_callbacks_integration.py`
    - `test_on_agent_start_end_called_with_expected_args`
    - `test_on_tool_message_called_with_arguments_and_result`
  - Use callback spies/mocks to assert calls and payloads.

## Notes

- Fast tests only unless explicitly marked slow. Keep OrchestratorTool tests under `@pytest.mark.slow` as they hit a real LLM.
- Use just test to run: `just test`.
- I can implement these in phases (start with the High-priority list) or all at once.