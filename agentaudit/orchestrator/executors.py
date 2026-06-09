"""Execute specialist agents against shared pipeline state."""

from agentaudit.agents import (
    judge_agent,
    parse_json,
    planner_agent,
    worker_agent,
    worker_retry_agent,
)
from agentaudit.tools.web_search import fetch_task_search_context


def run_specialist(agent_name: str, state) -> str:
    """Run a specialist agent and update state. Returns a short status message."""

    if agent_name == "planner":
        response = planner_agent(state.task)
        state.plan = parse_json(response.text)
        state.current_step_index = 0
        state.step_outputs = {}
        state.search_context = fetch_task_search_context(state.task)
        state.sync_current_step()
        return f"Plan created. Step 1: {state.current_step}"

    if agent_name == "worker":
        if not state.current_step:
            raise RuntimeError("Worker called before plan/step exists")
        step_num = state.current_step_index + 1
        prior = "\n".join(
            f"Step {i + 1}: {text}" for i, text in sorted(state.step_outputs.items())
        )
        response = worker_agent(
            state.current_step, state.task, prior, state.search_context
        )
        state.worker_output = response.text
        state.worker_attempts += 1
        state.verdict = None
        return f"Worker finished step {step_num}."

    if agent_name == "worker_retry":
        if state.worker_output is None or state.verdict is None:
            raise RuntimeError(
                f"Retry called without prior worker output or verdict "
                f"(output={'set' if state.worker_output is not None else 'missing'}, "
                f"verdict={'set' if state.verdict is not None else 'missing'}, "
                f"attempts={state.worker_attempts})"
            )
        step_num = state.current_step_index + 1
        feedback = state.verdict.get("suggestion") or "; ".join(
            state.verdict.get("issues", [])
        )
        response = worker_retry_agent(
            state.current_step or "",
            state.task,
            state.worker_output,
            feedback,
            state.search_context,
        )
        state.worker_output = response.text
        state.worker_attempts += 1
        state.verdict = None
        return f"Worker revised output for step {step_num}."

    if agent_name == "judge":
        if not state.worker_output or not state.current_step:
            raise RuntimeError("Judge called without worker output")
        step_num = state.current_step_index + 1
        response = judge_agent(state.task, state.current_step, state.worker_output)
        state.verdict = parse_json(response.text)
        passed = state.verdict.get("pass")
        score = state.verdict.get("score")

        if passed:
            state.record_step_pass()
            if state.has_more_steps():
                state.advance_to_next_step()
                return (
                    f"Judge PASS for step {step_num} (score {score}). "
                    f"Ready for step {state.current_step_index + 1}."
                )
            return f"Judge PASS for step {step_num} (score {score}). All steps complete."

        return f"Judge FAIL for step {step_num} (score {score})"

    raise ValueError(f"Unknown specialist agent: {agent_name}")
