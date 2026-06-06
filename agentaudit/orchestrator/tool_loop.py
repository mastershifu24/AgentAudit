import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from agentaudit.llm.openai import call_openai_with_tools
from agentaudit.orchestrator.executors import run_specialist
from agentaudit.orchestrator.pipeline_state import PipelineState
from agentaudit.orchestrator.tools import TOOL_DEFINITIONS, TOOL_TO_SPECIALIST
from agentaudit.trace import trace_llm

MAX_TURNS = 18

SYSTEM_PROMPT = """You are the orchestrator for AgentAudit. You coordinate specialist agents
by calling tools. You never do the work yourself.

Typical order:
1. run_planner — if no plan yet
2. run_worker — execute current plan step
3. run_judge — QC worker output for that step only
4. If judge passes and more steps remain → run_worker for next step → run_judge
5. run_worker_retry — if judge failed and retries remain, then run_judge again
6. finish_pipeline — when all_steps_passed is true OR judge failed with no retries left

Call exactly one tool per turn. Check state summary for current_step_index and steps_passed."""


@dataclass
class ToolTurnResult:
    """Return shape for @trace_llm plus the raw assistant message for tool routing."""

    text: str
    usage_metadata: SimpleNamespace
    assistant_message: Any


@trace_llm(agent_name="orchestrator_tools")
def _orchestrator_turn(messages: list[dict]) -> ToolTurnResult:
    completion = call_openai_with_tools(messages, TOOL_DEFINITIONS)
    message = completion.choices[0].message
    if message.tool_calls:
        text = json.dumps(
            {"tools_called": [tc.function.name for tc in message.tool_calls]}
        )
    else:
        text = message.content or ""
    usage = completion.usage
    return ToolTurnResult(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=usage.prompt_tokens if usage else None,
            candidates_token_count=usage.completion_tokens if usage else None,
        ),
        assistant_message=message,
    )


def _handle_tool_call(tool_name: str, state: PipelineState) -> str:
    if tool_name == "finish_pipeline":
        state.finished = True
        return "Pipeline marked complete."

    specialist = TOOL_TO_SPECIALIST.get(tool_name)
    if not specialist:
        return f"Unknown tool: {tool_name}"
    return run_specialist(specialist, state)


def run_tools_pipeline(task: str, state: PipelineState | None = None) -> PipelineState:
    state = state or PipelineState(task=task)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Task: {task}\n\n"
                f"Current state:\n{state.summary()}\n\n"
                "Call the next tool."
            ),
        },
    ]

    for turn in range(1, MAX_TURNS + 1):
        turn_result = _orchestrator_turn(messages)
        message = turn_result.assistant_message

        if not message.tool_calls:
            print(f"Turn {turn} — orchestrator returned text (no tool call). Stopping.\n")
            if message.content:
                print(f"  Message: {message.content}\n")
            break

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            print(f"Turn {turn} — orchestrator calls tool: {tool_name}")

            result = _handle_tool_call(tool_name, state)
            print(f"  Result: {result}\n")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

            if state.finished:
                print("Pipeline complete.\n")
                return state

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Updated state:\n{state.summary()}\n\n"
                    "Call the next tool or finish_pipeline."
                ),
            }
        )
    else:
        print(f"Stopped after {MAX_TURNS} turns (safety limit).\n")

    return state
