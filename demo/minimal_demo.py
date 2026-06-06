"""
Minimal AgentAudit demo: fixed pipeline (planner -> worker -> judge).

Run from project root:
    python -m demo.minimal_demo
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentaudit.agents import (
    judge_agent,
    parse_json,
    planner_agent,
    worker_agent,
    worker_retry_agent,
)
from agentaudit.trace import init_trace


def _print_verdict(verdict: dict, label: str) -> None:
    print(f"{label}:")
    print(json.dumps(verdict, indent=2))
    print()
    passed = verdict.get("pass")
    print(f"Result: {'PASS' if passed else 'FAIL'} (score: {verdict.get('score')})")
    if not passed and verdict.get("suggestion"):
        print(f"Suggestion: {verdict['suggestion']}")
    print()


def main() -> None:
    task = (
        "Research three skills needed for a junior data engineer role "
        "and explain each in one sentence."
    )
    trace_id = init_trace()

    print(f"AgentAudit demo — trace_id: {trace_id}\n")
    print(f"Task: {task}\n")

    plan_response = planner_agent(task)
    plan = parse_json(plan_response.text)
    step_one = plan["steps"][0]["action"]

    print("Planner output:")
    print(json.dumps(plan, indent=2))
    print()

    worker_response = worker_agent(step_one, task)
    worker_text = worker_response.text

    print("Worker output (attempt 1):")
    print(worker_text)
    print()

    judge_response = judge_agent(task, step_one, worker_text)
    verdict = parse_json(judge_response.text)
    _print_verdict(verdict, "Judge verdict (attempt 1)")

    if not verdict.get("pass"):
        feedback = verdict.get("suggestion") or "; ".join(verdict.get("issues", []))
        print("Retrying worker with judge feedback...\n")

        worker_response = worker_retry_agent(step_one, task, worker_text, feedback)
        worker_text = worker_response.text

        print("Worker output (attempt 2 — revised):")
        print(worker_text)
        print()

        judge_response = judge_agent(task, step_one, worker_text)
        verdict = parse_json(judge_response.text)
        _print_verdict(verdict, "Judge verdict (attempt 2)")

    print("Spans written to traces.jsonl")


if __name__ == "__main__":
    main()
