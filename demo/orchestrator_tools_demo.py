"""
Orchestrator with OpenAI tools (Level 3 multi-agent).

The orchestrator calls specialist agents as tools — run_planner, run_worker, etc.

Run from project root:
    python -m demo.orchestrator_tools_demo
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentaudit.orchestrator import run_tools_pipeline
from agentaudit.trace import init_trace


def main() -> None:
    task = (
        "Research three skills needed for a junior data engineer role "
        "and explain each in one sentence."
    )
    trace_id = init_trace()

    print(f"AgentAudit tools demo — trace_id: {trace_id}\n")
    print(f"Task: {task}\n")
    print("Orchestrator delegates via OpenAI function calling (tools).\n")

    state = run_tools_pipeline(task)

    print("=" * 50)
    print("Final state")
    print("=" * 50)
    if state.plan:
        print("\nPlan:")
        print(json.dumps(state.plan, indent=2))
    if state.worker_output:
        print("\nWorker output:")
        print(state.worker_output)
    if state.verdict:
        print("\nFinal verdict:")
        print(json.dumps(state.verdict, indent=2))
        passed = state.verdict.get("pass")
        print(f"\nLast step result: {'PASS' if passed else 'FAIL'} (score: {state.verdict.get('score')})")

    if state.step_outputs:
        print("\nCompleted step outputs:")
        for idx in sorted(state.step_outputs):
            print(f"\n--- Step {idx + 1} ---")
            print(state.step_outputs[idx])

    if state.all_steps_passed():
        print("\nAll plan steps passed QC.")

    print("\nSpans written to traces.jsonl")


if __name__ == "__main__":
    main()
