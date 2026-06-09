# AgentAudit

Observability + quality-check loops for multi-agent pipelines. Every LLM call is logged as a structured span; a judge agent scores outputs and records pass/fail.

Built for **LLM agent workflows** where you need more than a chatbox: per-step quality control, automatic retry, and a full audit trail — useful in **regulated domains** (tax, finance, compliance) where teams must show *what* each agent did, not just the final answer.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # Windows — creates the file the app actually reads
```

**Important:** Put your real key in `.env`, not `.env.example`.
`.env.example` is only a template (safe to commit). The app loads `.env` via `python-dotenv`.

Get an API key at https://platform.openai.com/api-keys.

Default model is **gpt-4o-mini** (cheap, good for multi-agent demos). Override with `OPENAI_MODEL` in `.env` (e.g. `gpt-4o` for richer answers on Streamlit Cloud).

**Web search** (optional, on by default): after planning, the worker gets DuckDuckGo snippets via the `ddgs` package — no extra API key. Set `AGENTAUDIT_WEB_SEARCH=false` to disable. Paste a long job description into the task to skip search and use your text instead.

## Run the demos

**Fixed pipeline** (Python hardcodes order):

```bash
python -m demo.minimal_demo
```

**Orchestrator-driven** (LLM picks which agent runs next):

```bash
python -m demo.orchestrator_demo
```

**Orchestrator + tools** (Level 3 — LLM calls agents as functions):

```bash
python -m demo.orchestrator_tools_demo
```

Both run a planner → worker → judge flow with retry on failure. The orchestrator demo adds an `orchestrator` agent that routes specialists. The tools demo uses OpenAI function calling (`run_planner`, `run_worker`, etc.). All steps are traced to `traces.jsonl`.

See [docs/DESIGN.md](docs/DESIGN.md) for architecture diagrams and routing rules.

## Run the app (dashboard)

```bash
streamlit run dashboard/app.py
```

Opens a local UI where you can **enter a task**, run the orchestrator pipeline, see the final answer + QC verdict, and inspect the full audit trail. Use the **Interview guide** tab when prepping for demos.

See [docs/INTERVIEW.md](docs/INTERVIEW.md) for recruiter/engineer talking points.

## What this demonstrates (e.g. tax / data science roles)

| Job theme | How AgentAudit maps |
|-----------|---------------------|
| **LLM prompting & deployment** | Planner, worker, judge prompts; OpenAI API; configurable model |
| **AI agents** | Multi-agent pipeline with orchestration and retry |
| **Python** | End-to-end app: agents, tracing, Streamlit UI |
| **Quality in regulated work** | Per-step judge pass/fail; span logs (input, output, latency, tokens) |
| **Integrating AI into workflows** | Fixed pipeline pattern you can extend with tools (web search, APIs, ERP hooks) |

## Project layout

```
agentaudit/
  trace/          # @trace_llm decorator, context, JSONL store + reader
  llm/            # OpenAI client
  agents/          # planner, worker, judge, orchestrator LLM functions
  tools/           # web search (ddgs) for worker grounding
  orchestrator/    # PipelineState + run loop
demo/
  minimal_demo.py      # fixed pipeline
  orchestrator_demo.py      # Level 2: JSON routing
  orchestrator_tools_demo.py # Level 3: tools / function calling
dashboard/
  app.py          # Streamlit trace viewer
docs/
  DESIGN.md       # architecture reference
```

## Sample span

```json
{
  "trace_id": "...",
  "span_id": "...",
  "parent_span_id": null,
  "agent_name": "planner",
  "timestamp": "2026-06-06T12:00:00+00:00",
  "input": "...",
  "output": "...",
  "latency_ms": 842.15,
  "tokens_in": 120,
  "tokens_out": 85,
  "status": "ok"
}
```

The worker span will have `parent_span_id` pointing at the planner span when nested under the same run.

## Next steps

- [x] Judge agent that scores worker output
- [x] Streamlit trace viewer
- [ ] SQLite store (optional upgrade from JSONL)
- [x] Retry loop when judge fails
