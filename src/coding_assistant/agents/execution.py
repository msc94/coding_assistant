import asyncio
import dataclasses
import json
import logging
import re
import textwrap
from json import JSONDecodeError

from opentelemetry import trace

from coding_assistant.agents.callbacks import AgentCallbacks
from coding_assistant.agents.history import append_assistant_message, append_tool_message, append_user_message
from coding_assistant.agents.interrupts import InterruptibleSection, NonInterruptibleSection
from coding_assistant.agents.parameters import format_parameters
from coding_assistant.agents.types import (
    Agent,
    AgentOutput,
    Completer,
    FinishTaskResult,
    ShortenConversationResult,
    TextResult,
)
from coding_assistant.llm.adapters import execute_tool_call, get_tools
from coding_assistant.ui import UI

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


START_MESSAGE_TEMPLATE = """
You are an agent named `{name}`.

## Task

Your client has been given the following description of your work and capabilities: 

{description}

## Parameters

Your client has provided the following parameters for your task:

{parameters}
""".strip()

FEEDBACK_TEMPLATE = """
Your client has provided the following feedback on your work:

{feedback}

Please rework your result to address the feedback.
Afterwards, call the `finish_task` tool again to signal that you are done.
""".strip()


def _create_start_message(agent: Agent) -> str:
    parameters_str = format_parameters(agent.parameters)
    message = START_MESSAGE_TEMPLATE.format(
        name=agent.name,
        description=textwrap.indent(agent.description, "> "),
        parameters=parameters_str,
    )

    return message


def _handle_finish_task_result(result: FinishTaskResult, agent: Agent):
    agent.output = AgentOutput(
        result=result.result,
        summary=result.summary,
    )
    return "Agent output set."


def _handle_text_result(result: TextResult, function_name: str, no_truncate_tools: set[str]) -> str:
    if len(result.content) >= 50_000 and not any(re.search(pattern, function_name) for pattern in no_truncate_tools):
        return "System error: Tool call result too long. Please use a tool or arguments that return shorter results."
    return result.content


def _handle_shorten_conversation_result(
    result: ShortenConversationResult, agent: Agent, agent_callbacks: AgentCallbacks
):
    start_message = _create_start_message(agent)
    agent.history = []
    append_user_message(
        agent.history,
        agent_callbacks,
        agent.name,
        start_message,
    )
    append_user_message(
        agent.history,
        agent_callbacks,
        agent.name,
        f"A summary of your conversation with the client until now:\n\n{result.summary}\n\nPlease continue your work.",
    )
    return "Conversation shortened and history reset."


@tracer.start_as_current_span("handle_tool_call")
async def handle_tool_call(
    tool_call,
    agent: Agent,
    agent_callbacks: AgentCallbacks,
    no_truncate_tools: set[str],
    tool_confirmation_patterns: list[str],
    *,
    ui: UI,
):
    function_name = tool_call.function.name

    args_str = tool_call.function.arguments or "{}"
    try:
        function_args = json.loads(args_str)
    except JSONDecodeError as e:
        logger.error(
            f"[{agent.name}] [{tool_call.id}] Failed to parse tool '{function_name}' arguments as JSON: {e} | raw: {args_str}"
        )
        append_tool_message(
            agent.history,
            agent_callbacks,
            agent.name,
            tool_call.id,
            function_name,
            None,
            f"Error: Tool call arguments {args_str} are not valid JSON: {e}",
        )
        return

    for pattern in tool_confirmation_patterns:
        if re.search(pattern, function_name):
            question = f"Execute tool `{function_name}` with arguments `{function_args}`?"
            answer = await ui.confirm(question)
            if not answer:
                append_tool_message(
                    agent.history,
                    agent_callbacks,
                    agent.name,
                    tool_call.id,
                    function_name,
                    function_args,
                    "Tool execution denied.",
                )
                return

    trace.get_current_span().set_attribute("function.name", function_name)
    trace.get_current_span().set_attribute("function.args", json.dumps(function_args))

    logger.info(f"[{tool_call.id}] [{agent.name}] Calling tool '{function_name}' with arguments {function_args}")

    try:
        function_call_result = await execute_tool_call(function_name, function_args, agent.tools)
    except ValueError as e:
        append_tool_message(
            agent.history,
            agent_callbacks,
            agent.name,
            tool_call.id,
            function_name,
            function_args,
            f"Error executing tool: {e}",
        )
        return

    trace.get_current_span().set_attribute("function.result", str(function_call_result))

    result_handlers = {
        FinishTaskResult: lambda r: _handle_finish_task_result(r, agent),
        ShortenConversationResult: lambda r: _handle_shorten_conversation_result(r, agent, agent_callbacks),
        TextResult: lambda r: _handle_text_result(r, function_name, no_truncate_tools),
    }

    tool_return_summary = result_handlers[type(function_call_result)](function_call_result)

    append_tool_message(
        agent.history,
        agent_callbacks,
        agent.name,
        tool_call.id,
        function_name,
        function_args,
        tool_return_summary,
    )


@tracer.start_as_current_span("handle_tool_calls")
async def handle_tool_calls(
    message,
    agent: Agent,
    agent_callbacks: AgentCallbacks,
    no_truncate_tools: set[str],
    tool_confirmation_patterns: list[str],
    *,
    ui: UI,
):
    tool_calls = message.tool_calls
    trace.get_current_span().set_attribute("message.tool_calls", tool_calls)

    if not tool_calls:
        append_user_message(
            agent.history,
            agent_callbacks,
            agent.name,
            "I detected a step from you without any tool calls. This is not allowed. If you want to ask the client something, please use the `ask_user` tool. If you are done with your task, please call the `finish_task` tool to signal that you are done. Otherwise, continue your work.",
        )
        return

    aws = []
    for tool_call in tool_calls:
        task = asyncio.create_task(
            handle_tool_call(
                tool_call,
                agent,
                agent_callbacks,
                no_truncate_tools,
                tool_confirmation_patterns,
                ui=ui,
            ),
            name=f"{tool_call.function.name} ({tool_call.id})",
        )
        aws.append(task)

    while True:
        done, pending = await asyncio.wait(aws, return_when=asyncio.FIRST_COMPLETED, timeout=0.2)

        # await the task, which will throw any exceptions stored in the future.
        for task in done:
            await task

        if not pending:
            break


@tracer.start_as_current_span("do_single_step")
async def do_single_step(
    agent: Agent,
    agent_callbacks: AgentCallbacks,
    shorten_conversation_at_tokens: int,
    no_truncate_tools: set[str],
    *,
    completer: Completer,
    ui: UI,
    tool_confirmation_patterns: list[str],
):
    trace.get_current_span().set_attribute("agent.name", agent.name)

    # Validate agent tools
    if not any(tool.name() == "finish_task" for tool in agent.tools):
        raise RuntimeError("Agent needs to have a `finish_task` tool in order to run a step.")
    if not any(tool.name() == "shorten_conversation" for tool in agent.tools):
        raise RuntimeError("Agent needs to have a `shorten_conversation` tool in order to run a step.")

    tools = await get_tools(agent.tools)
    trace.get_current_span().set_attribute("agent.tools", json.dumps(tools))

    if not agent.history:
        raise RuntimeError("Agent needs to have history in order to run a step.")
    trace.get_current_span().set_attribute("agent.history", json.dumps(agent.history))

    completion = await completer(
        agent.history,
        model=agent.model,
        tools=tools,
        callbacks=agent_callbacks,
    )
    message = completion.message
    trace.get_current_span().set_attribute("completion.message", message.model_dump_json())

    if hasattr(message, "reasoning_content") and message.reasoning_content:
        trace.get_current_span().set_attribute("completion.reasoning_content", message.reasoning_content)
        agent_callbacks.on_assistant_reasoning(agent.name, message.reasoning_content)

        # We delete reasoning so we don't store it in the history, and hence do not send it to the LLM again.
        del message.reasoning_content

    append_assistant_message(agent.history, agent_callbacks, agent.name, message)
    await handle_tool_calls(
        message,
        agent,
        agent_callbacks,
        no_truncate_tools,
        tool_confirmation_patterns,
        ui=ui,
    )

    # Check conversation length and request shortening if needed
    if completion.tokens > shorten_conversation_at_tokens:
        append_user_message(
            agent.history,
            agent_callbacks,
            agent.name,
            "Your conversation history has grown too large. Please summarize it by using the `shorten_conversation` tool.",
        )

    return message


@tracer.start_as_current_span("run_agent_loop")
async def run_agent_loop(
    agent: Agent,
    agent_callbacks: AgentCallbacks,
    *,
    completer: Completer,
    ui: UI,
    shorten_conversation_at_tokens: int = 200_000,
    no_truncate_tools: set[str] = set(),
    tool_confirmation_patterns: list[str] = [],
    enable_user_feedback: bool = False,
    is_interruptible: bool = False,
) -> AgentOutput:
    if agent.output:
        raise RuntimeError("Agent already has a result or summary.")

    trace.get_current_span().set_attribute("agent.name", agent.name)
    parameters_json = json.dumps([dataclasses.asdict(p) for p in agent.parameters])
    trace.get_current_span().set_attribute("agent.parameter_description", parameters_json)

    start_message = _create_start_message(agent)
    agent_callbacks.on_agent_start(agent.name, agent.model, is_resuming=bool(agent.history))
    append_user_message(agent.history, agent_callbacks, agent.name, start_message)

    while True:
        while not agent.output:
            section_cls = InterruptibleSection if is_interruptible else NonInterruptibleSection
            with section_cls() as interruptible_section:
                await do_single_step(
                    agent,
                    agent_callbacks,
                    shorten_conversation_at_tokens,
                    no_truncate_tools,
                    completer=completer,
                    ui=ui,
                    tool_confirmation_patterns=tool_confirmation_patterns,
                )

            if interruptible_section.was_interrupted:
                logger.info(f"Agent '{agent.name}' was interrupted during execution.")
                feedback = await ui.ask("Feedback: ")
                formatted_feedback = FEEDBACK_TEMPLATE.format(
                    feedback=textwrap.indent(feedback, "> "),
                )
                append_user_message(agent.history, agent_callbacks, agent.name, formatted_feedback)

        trace.get_current_span().set_attribute("agent.result", agent.output.result)
        trace.get_current_span().set_attribute("agent.summary", agent.output.summary)
        agent_callbacks.on_agent_end(agent.name, agent.output.result, agent.output.summary)

        feedback: str = "Ok"
        if enable_user_feedback:
            feedback = await ui.ask(f"Feedback for {agent.name}", default="Ok")

        if feedback != "Ok":
            formatted_feedback = FEEDBACK_TEMPLATE.format(feedback=textwrap.indent(feedback, "> "))
            append_user_message(agent.history, agent_callbacks, agent.name, formatted_feedback)
            agent.output = None  # continue loop
        else:
            break

    return agent.output
