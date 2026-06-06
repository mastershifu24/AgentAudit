# AgentAudit — Architecture Design

## Problem

Multi-agent LLM pipelines fail in ways that are hard to debug:

- Which agent made the wrong decision?
- Did the worker follow its assigned step or drift?
- Can bad output be caught before it propagates?

AgentAudit adds **structured tracing** and a **judge QC loop** to answer those questions.

---

## Three demo modes

### 1. Fixed pipeline (`demo/minimal_demo.py`) — Level 1

```
Python main() hardcodes:
  planner → worker → judge → (retry?) → judge
```

**What it proves:** Tracing, judge, retry loop.

**Limitation:** You (Python) decide the order — agents don't coordinate.

### 2. Orchestrator JSON routing (`demo/orchestrator_demo.py`) — Level 2

```
loop:
  orchestrator LLM → returns {"next_agent": "worker"}
  Python → runs that specialist
  update shared state
  until orchestrator says "done"
```

**What it proves:** An agent decides which other agent runs next.

**Safety:** Invalid orchestrator choices fall back to deterministic routing.

### 3. Orchestrator + tools (`demo/orchestrator_tools_demo.py`) — Level 3

```
loop:
  orchestrator LLM → calls tool run_worker()
  Python → executes tool → runs specialist
  tool result → back to orchestrator
  until finish_pipeline tool
```

**What it proves:** Agents-as-tools pattern (OpenAI function calling). Same as production LangChain / Assistants style.

**Key difference from Level 2:** Orchestrator doesn't describe the next agent in JSON — it **invokes** it like a function.

---

## Component diagram

```
┌─────────────────────────────────────────────────────────┐
│                    orchestrator_demo                     │
│  ┌──────────────┐    ┌─────────────────────────────┐  │
│  │ Orchestrator │───▶│ PipelineState (shared memory)│  │
│  │   (LLM)      │    │ plan, worker_output, verdict │  │
│  └──────┬───────┘    └─────────────────────────────┘  │
│         │ picks next_agent                             │
│         ▼                                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Specialist agents (agentaudit/agents/specialists.py)│  │
│  │  planner | worker | worker_retry | judge         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │ every LLM call wrapped by @trace_llm
         ▼
┌─────────────────┐     ┌──────────────────┐
│  traces.jsonl   │────▶│ dashboard/app.py │
└─────────────────┘     └──────────────────┘
```

---

## Trace model (spans)

Each LLM call = one **span**:

| Field | Meaning |
|-------|---------|
| `trace_id` | One pipeline run |
| `span_id` | One LLM call |
| `parent_span_id` | Links child → parent agent call |
| `agent_name` | planner, worker, judge, orchestrator, … |
| `input` / `output` | Prompt and response |
| `latency_ms`, `tokens_in/out` | Cost/perf |
| `verdict`, `score` | Judge-only extras |

Orchestrator spans appear in the trace tree — you can see *why* each agent ran.

---

## Shared state (`PipelineState`)

```python
task              # original user goal
plan              # planner JSON output
current_step      # step 1 action from plan
worker_output     # latest worker text
verdict           # latest judge JSON
worker_attempts   # retry counter
```

Orchestrator reads a **summary** of this state each turn and returns:

```json
{"next_agent": "worker", "reason": "Plan exists but worker has not run yet."}
```

---

## Routing rules (orchestrator + fallback)

| State | Expected next agent |
|-------|---------------------|
| No plan | planner |
| Plan, no worker output | worker |
| Worker output, no verdict | judge |
| Verdict fail, retries left | worker_retry |
| Verdict pass OR no retries | done |

If the orchestrator LLM returns an invalid agent name, Python uses this table as fallback.

---

## File map

```
agentaudit/
  trace/           @trace_llm, context, JSONL store, reader
  llm/             OpenAI client
  orchestrator/    PipelineState + run loop
demo/
  minimal_demo.py      Fixed pipeline
  orchestrator_demo.py Orchestrator-driven pipeline
agentaudit/agents/
  specialists.py       All LLM agent functions
dashboard/
  app.py           Streamlit viewer
```

---

## Next evolution (Level 3)

**Agents as tools:** Give the orchestrator function-calling access to specialists instead of a loop in Python. Same architecture, tighter coupling.

---

## Resume one-liner

> Built AgentAudit: orchestrator-driven multi-agent pipeline with structured LLM tracing, automated judge QC, and retry-on-failure — local JSONL spans + Streamlit debug UI.
