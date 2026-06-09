from agentaudit.agents import orchestrator_agent, parse_json
from agentaudit.orchestrator.executors import run_specialist
from agentaudit.orchestrator.pipeline_state import PipelineState

MAX_TURNS = 12
VALID_AGENTS = {"planner", "worker", "judge", "worker_retry", "done"}


def _suggest_next_agent(state: PipelineState) -> str:
    if state.plan is None:
        return "planner"
    if state.all_steps_passed():
        return "done"
    if state.worker_output is None:
        return "worker"
    if state.verdict is None:
        return "judge"
    if state.verdict.get("pass"):
        if state.has_more_steps():
            return "worker"
        return "done"
    if state.worker_attempts < state.max_worker_attempts:
        return "worker_retry"
    return "done"


def run_orchestrated_pipeline(task: str, state: PipelineState | None = None) -> PipelineState:
    state = state or PipelineState(task=task)

    for turn in range(1, MAX_TURNS + 1):
        response = orchestrator_agent(state.task, state.summary())
        decision = parse_json(response.text)

        next_agent = decision.get("next_agent", "").strip().lower()
        state.last_orchestrator_reason = decision.get("reason", "")

        suggested = _suggest_next_agent(state)
        if next_agent not in VALID_AGENTS:
            next_agent = suggested
            state.last_orchestrator_reason = (
                f"Fallback routing (orchestrator returned invalid agent): {next_agent}"
            )
        elif next_agent != suggested:
            state.last_orchestrator_reason = (
                f"Fallback routing (orchestrator chose '{next_agent}', "
                f"expected '{suggested}'): {decision.get('reason', '')}"
            )
            next_agent = suggested

        print(f"Turn {turn} — orchestrator → {next_agent}")
        print(f"  Reason: {state.last_orchestrator_reason}")

        if next_agent == "done":
            state.finished = True
            print("  Pipeline complete.\n")
            break

        run_specialist(next_agent, state)
        print(f"  {next_agent} finished.\n")
    else:
        print(f"Stopped after {MAX_TURNS} turns (safety limit).\n")

    return state
