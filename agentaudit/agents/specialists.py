"""Specialist agents — planner, worker, judge, orchestrator (each traced via @trace_llm)."""

import json
import re

from agentaudit.llm.openai import LLMResponse, call_openai
from agentaudit.trace import trace_llm
from agentaudit.agents.judge_utils import normalize_verdict


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Expected JSON in response. Got:\n{text}")
    return json.loads(match.group())


@trace_llm(agent_name="planner")
def planner_agent(task: str):
    prompt = f"""You are a planner agent. Break this task into exactly 2 steps.

Task: {task}

Return ONLY valid JSON in this shape:
{{
  "steps": [
    {{"step": 1, "action": "..."}},
    {{"step": 2, "action": "..."}}
  ]
}}
"""
    return call_openai(prompt)


@trace_llm(agent_name="worker")
def worker_agent(step_action: str, original_task: str, prior_outputs: str = ""):
    prior_block = (
        f"\nOutputs from earlier steps (use as context):\n{prior_outputs}\n"
        if prior_outputs
        else ""
    )
    prompt = f"""You are a worker agent. Execute this step and return a concise result.

Original task (for context): {original_task}
{prior_block}
Step to execute: {step_action}
"""
    return call_openai(prompt)


@trace_llm(agent_name="worker_retry")
def worker_retry_agent(
    step_action: str,
    original_task: str,
    previous_output: str,
    judge_feedback: str,
):
    prompt = f"""You are a worker agent revising your output after a quality-check failure.

Original task (for context): {original_task}

Step to execute (do ONLY this — no more, no less): {step_action}

Your previous output:
{previous_output}

Judge feedback — fix these issues:
{judge_feedback}

Return a revised result that stays within the assigned step's scope.
"""
    return call_openai(prompt)


@trace_llm(agent_name="judge")
def judge_agent(original_task: str, assigned_step: str, worker_output: str):
    prompt = f"""You are a quality-check judge for a multi-agent pipeline.

Judge ONLY whether the worker completed the ASSIGNED STEP below.
Do NOT judge against the full original task if that would require a later step.

Original task (context only — do not require all of this on one step):
{original_task}

Assigned step (judge against THIS only):
{assigned_step}

Worker output:
{worker_output}

Rules:
1. If the assigned step says identify/list/research skills: PASS when items are listed
   without explanations. FAIL only if they added explanations (scope creep) or listed too few items.
2. If the assigned step says explain or one sentence each: PASS only if each item has
   a clear one-sentence explanation. FAIL if explanations are missing.
3. Do NOT fail for formatting style (numbered list vs bullets) if content is correct.
4. Do NOT fail because a LATER step's work is missing — that is expected.
5. If the worker satisfied the assigned step, you MUST set pass=true and issues=[].

Return ONLY valid JSON:
{{
  "pass": true,
  "score": 90,
  "issues": [],
  "suggestion": ""
}}
"""
    response = call_openai(prompt)
    verdict = normalize_verdict(parse_json(response.text))
    return LLMResponse(
        text=json.dumps(verdict, indent=2),
        usage_metadata=response.usage_metadata,
    )


@trace_llm(agent_name="orchestrator")
def orchestrator_agent(task: str, state_summary: str):
    prompt = f"""You are the orchestrator agent. You coordinate specialist agents.
You do NOT do the work yourself — you decide which agent runs next.

Original task:
{task}

Current pipeline state:
{state_summary}

Available agents (pick exactly one):
- planner       — create a 2-step plan (use when plan is missing)
- worker        — execute the current plan step (use when no worker output for current step)
- judge         — quality-check worker output for the current step only
- worker_retry  — revise worker output after judge failure (when retries remain)
- done          — all plan steps passed QC, or retries exhausted on final step

Rules:
1. Start with planner if there is no plan.
2. Run worker for the current step, then judge that step only.
3. If judge passes and more steps remain, run worker for the next step, then judge again.
4. If judge fails and worker_attempts < max_worker_attempts, run worker_retry then judge again.
5. Return done when all_steps_passed is true, or judge failed with no retries left.

Return ONLY valid JSON:
{{
  "next_agent": "planner",
  "reason": "one sentence explaining why this agent runs next"
}}
"""
    return call_openai(prompt)
