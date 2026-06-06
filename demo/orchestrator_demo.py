"""
Orchestrator-driven multi-agent demo.

The orchestrator LLM decides which specialist runs next (planner, worker, judge, etc.).
Python executes the decision and updates shared state.

Run from project root:
    python -m demo.orchestrator_demo
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentaudit.orchestrator import run_orchestrated_pipeline
from agentaudit.trace import init_trace


def main() -> None:
    task = (
        "Research three skills needed for a junior data engineer role "
        "and explain each in one sentence."
    )
    trace_id = init_trace()

    print(f"AgentAudit orchestrator demo — trace_id: {trace_id}\n")
    print(f"Task: {task}\n")
    print("The orchestrator agent decides which specialist runs next.\n")

    state = run_orchestrated_pipeline(task)

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
        print(f"\nResult: {'PASS' if passed else 'FAIL'} (score: {state.verdict.get('score')})")

    print("\nSpans written to traces.jsonl")


if __name__ == "__main__":
    main()
