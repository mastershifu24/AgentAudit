"""Fixed pipeline — deterministic planner → worker → judge (no orchestrator LLM)."""

from agentaudit.debug_log import debug
from agentaudit.orchestrator.executors import run_specialist
from agentaudit.orchestrator.pipeline_state import PipelineState


def run_fixed_pipeline(task: str, state: PipelineState | None = None) -> PipelineState:
    """Run all plan steps with QC. Fewer LLM calls than orchestrator routing."""
    state = state or PipelineState(task=task)
    debug(f"pipeline start task={task[:60]!r}")
    run_specialist("planner", state)
    debug(f"plan steps={state.total_steps()}")

    while not state.all_steps_passed():
        step = state.current_step_index + 1
        run_specialist("worker", state)
        debug(f"step {step} worker done attempts={state.worker_attempts} output_len={len(state.worker_output or '')}")

        passed = False
        while True:
            steps_before = len(state.step_outputs)
            run_specialist("judge", state)
            # Judge clears verdict on pass+advance — check step_outputs, not verdict.
            if len(state.step_outputs) > steps_before:
                debug(f"step {step} judge PASS (recorded)")
                passed = True
                break
            debug(f"step {step} judge FAIL score={state.verdict.get('score') if state.verdict else None}")
            if state.worker_attempts >= state.max_worker_attempts:
                debug(f"step {step} no retries left")
                break
            run_specialist("worker_retry", state)
            debug(f"step {step} retry done attempts={state.worker_attempts}")

        if not passed:
            state.finished = True
            debug("pipeline finished (failed QC)")
            return state

    state.finished = True
    debug(f"pipeline finished (pass) steps={len(state.step_outputs)}")
    return state
