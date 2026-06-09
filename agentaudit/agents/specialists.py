"""Specialist agents — planner, worker, judge, orchestrator (each traced via @trace_llm)."""

import json
import re

from agentaudit.llm.openai import LLMResponse, call_openai
from agentaudit.trace import trace_llm
from agentaudit.agents.judge_utils import normalize_verdict

WORKER_SYSTEM = """You produce specific, task-grounded answers — not generic textbook lists.

Rules:
- Anchor every point to names in the task (company, role, product, domain).
- Prefer concrete skills, tools, and methods over vague categories
  (e.g. "Python, Pandas, SQL" not "programming skills"; "LLM agents" not "AI knowledge").
- Match counts exactly (three items means exactly three).
- Do not open with meta phrases ("To execute the step", "I researched").
- Do not close with filler ("crucial for success", "in today's landscape").
- If web search snippets are provided, ground facts in those — prefer specifics from results.
- If the user pasted source text in the task, extract from that — do not invent a different list.
- If neither search nor pasted source exists, reason from the named context; avoid platitudes.
- Skip textbook definitions unless the step explicitly asks for them."""

WORKER_RETRY_SYSTEM = WORKER_SYSTEM + "\n- Fix only what the judge flagged; keep good specifics."


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Expected JSON in response. Got:\n{text}")
    return json.loads(match.group())


@trace_llm(agent_name="planner")
def planner_agent(task: str):
    prompt = f"""You are a planner agent. Break this task into 1–3 concrete steps.

Task: {task}

Rules:
- Match what the user asked — do not invent extra constraints they did not request.
- Use a single step when the task is one coherent request (e.g. research, explain, compare).
- Only split into separate list-then-explain steps when the user explicitly asked for
  names/titles first and explanations in a later step (e.g. "titles only, then summarize each").
- When a step must be names/titles only, say so explicitly (e.g. "names only, no explanations").
- For research tasks: plan steps that demand role- or company-specific detail, not textbook definitions.
  Do not add a redundant final "summarize" step if earlier steps already answer the task.
- Describe WHAT to do in each step — never include the actual answers/items.

Return ONLY valid JSON in this shape:
{{
  "steps": [
    {{"step": 1, "action": "..."}}
  ]
}}
"""
    return call_openai(prompt)


def _search_block(search_context: str) -> str:
    if not search_context.strip():
        return ""
    return (
        f"\nWeb search snippets (ground facts here when relevant):\n{search_context}\n"
    )


@trace_llm(agent_name="worker")
def worker_agent(
    step_action: str,
    original_task: str,
    prior_outputs: str = "",
    search_context: str = "",
):
    prior_block = (
        f"\nOutputs from earlier steps (use as context):\n{prior_outputs}\n"
        if prior_outputs
        else ""
    )
    prompt = f"""Execute this step. Return only the result — no preamble or wrap-up.

Original task (for context): {original_task}
{_search_block(search_context)}{prior_block}
Step to execute: {step_action}
"""
    return call_openai(prompt, system=WORKER_SYSTEM, temperature=0.4)


@trace_llm(agent_name="worker_retry")
def worker_retry_agent(
    step_action: str,
    original_task: str,
    previous_output: str,
    judge_feedback: str,
    search_context: str = "",
):
    prompt = f"""You are a worker agent revising your output after a quality-check failure.

Original task (for context): {original_task}
{_search_block(search_context)}
Step to execute (do ONLY this — no more, no less): {step_action}

Your previous output:
{previous_output}

Judge feedback — fix these issues:
{judge_feedback}

Return a revised result that stays within the assigned step's scope.
"""
    return call_openai(prompt, system=WORKER_RETRY_SYSTEM, temperature=0.4)


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
1. Judge ONLY the assigned step — not the full original task unless this step covers it all.
2. PASS when the worker reasonably completed what the assigned step asked for.
3. FAIL only for clear problems: wrong topic, too few items, scope creep (extra work the step
   forbade), or missing required content (e.g. step says "explain each" but only names were listed).
4. Do NOT fail for formatting (numbered list vs bullets) if content is correct.
5. Do NOT fail because a LATER step's work is missing — that is expected on multi-step tasks.
6. If the worker satisfied the assigned step, you MUST set pass=true and issues=[].

Return ONLY valid JSON:
{{
  "pass": true,
  "score": 90,
  "issues": [],
  "suggestion": ""
}}
"""
    response = call_openai(prompt)
    verdict = normalize_verdict(parse_json(response.text), assigned_step, worker_output)
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
