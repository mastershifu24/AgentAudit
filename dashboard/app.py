"""

AgentAudit — run multi-agent pipelines and inspect traces.



Run from project root:

    streamlit run dashboard/app.py

"""



import json

import sys

from pathlib import Path



sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



import streamlit as st



from agentaudit.orchestrator import run_fixed_pipeline

from agentaudit.trace import get_trace_id, init_trace

from agentaudit.trace.reader import group_by_trace, load_spans, summarize_trace

from agentaudit.trace.store import DEFAULT_LOG_PATH



DEFAULT_TASK = (

    "Research three skills needed for a junior data engineer role "

    "and explain each in one sentence."

)



st.set_page_config(page_title="AgentAudit", page_icon="🔍", layout="wide")



st.title("AgentAudit")

st.caption(

    "Multi-agent pipeline with quality checks and full audit trail — "

    "not a single chatbot response."

)





def _format_final_answer(state) -> str:

    if state.step_outputs:

        parts = []

        for index in sorted(state.step_outputs):

            parts.append(f"**Step {index + 1}**\n\n{state.step_outputs[index]}")

        return "\n\n---\n\n".join(parts)

    if state.worker_output:

        return state.worker_output

    return "_No worker output yet._"





def _run_pipeline(task: str) -> tuple[str, object]:

    trace_id = init_trace()

    state = run_fixed_pipeline(task)

    return trace_id, state





def _render_span(span: dict, index: int, key_prefix: str = "") -> None:

    agent = span["agent_name"]

    status = span.get("status", "ok")

    verdict = span.get("verdict")

    title = f"{index}. {agent} — {status}"

    if verdict:

        title += f" ({verdict}, score {span.get('score')})"



    with st.expander(title, expanded=(agent == "judge")):

        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

        meta_col1.write(f"**Span ID:** `{span['span_id'][:8]}…`")

        meta_col2.write(f"**Latency:** {span.get('latency_ms')} ms")

        meta_col3.write(f"**Tokens in/out:** {span.get('tokens_in')} / {span.get('tokens_out')}")

        meta_col4.write(f"**Time:** {span['timestamp'][:19]}")



        if span.get("parent_span_id"):

            st.write(f"**Parent span:** `{span['parent_span_id'][:8]}…`")



        sid = span["span_id"]

        st.text_area("Input", span.get("input", ""), height=120, key=f"{key_prefix}in-{sid}")

        st.text_area("Output", span.get("output", ""), height=200, key=f"{key_prefix}out-{sid}")





def _render_trace_detail(traces: dict, trace_id: str, key_prefix: str = "") -> None:

    selected_spans = traces[trace_id]

    summary = summarize_trace(selected_spans)



    detail_col1, detail_col2, detail_col3 = st.columns(3)

    detail_col1.write(f"**Trace ID:** `{summary['trace_id']}`")

    detail_col2.write(f"**Final verdict:** `{summary['final_verdict'] or '—'}`")

    detail_col3.write(f"**Total latency:** {summary['total_latency_ms']} ms")



    st.write(f"**Pipeline:** {summary['agents']}")



    for i, span in enumerate(selected_spans, start=1):

        _render_span(span, i, key_prefix=key_prefix)





with st.sidebar:

    st.markdown("### What is this?")

    st.markdown(

        """

**AgentAudit** runs a task through several AI agents:



1. **Planner** — breaks the task into steps

2. **Worker** — executes each step

3. **Judge** — scores quality (pass/fail)

4. **Retry** — fixes output if judge fails



Every LLM call is logged. You see *how* the answer was built, not just the answer.



**vs ChatGPT:** one chat = black box.  

**AgentAudit:** structured pipeline + QC + audit trail.

        """

    )

    st.markdown("### Tech stack")

    st.markdown(

        """

- Python + OpenAI API

- `@trace_llm` decorator → JSONL spans

- Orchestrator LLM + fallback routing

- Streamlit UI

        """

    )

    st.markdown(f"Traces: `{DEFAULT_LOG_PATH}`")

    if st.button("Reload"):

        st.rerun()

    if st.button("Clear trace history"):

        if DEFAULT_LOG_PATH.exists():

            DEFAULT_LOG_PATH.unlink()

        st.session_state.pop("last_state", None)

        st.session_state.pop("last_trace_id", None)

        st.rerun()



run_tab, history_tab, guide_tab = st.tabs(["Run pipeline", "Trace history", "Interview guide"])



with run_tab:

    st.subheader("Run a task")

    st.markdown(

        "Enter any multi-step task. Runs planner → worker → judge per step "

        "(with retry if quality fails)."

    )



    if "task_input" not in st.session_state:
        st.session_state["task_input"] = DEFAULT_TASK

    task = st.text_area(
        "Your task",
        key="task_input",
        height=100,
        placeholder="Enter a multi-step task…",
    )

    run_clicked = st.button("Run pipeline", type="primary")



    if run_clicked:

        task_to_run = task.strip() or DEFAULT_TASK

        with st.spinner("Running pipeline — planner, worker, judge per step…"):

            trace_id, state = _run_pipeline(task_to_run)

        st.session_state["last_trace_id"] = trace_id

        st.session_state["last_state"] = state



    if "last_state" in st.session_state:

        state = st.session_state["last_state"]

        trace_id = st.session_state.get("last_trace_id", get_trace_id())

        spans = load_spans(DEFAULT_LOG_PATH)
        traces = group_by_trace(spans)
        run_spans = traces.get(trace_id, [])
        summary = summarize_trace(run_spans) if run_spans else {}
        judge_scores = summary.get("judge_scores") or []
        passed = summary.get("final_verdict") == "pass"
        verdict_label = summary.get("final_verdict", "—").upper() if summary.get("final_verdict") else "—"
        if len(judge_scores) > 1:
            score_label = f"{min(judge_scores)} (min of {len(judge_scores)})"
        elif judge_scores:
            score_label = str(judge_scores[0])
        else:
            score_label = "—"



        st.divider()

        st.subheader("Results")



        m1, m2, m3, m4 = st.columns(4)

        m1.metric("QC verdict", verdict_label)

        m2.metric("Judge score", score_label)

        m3.metric("Steps completed", f"{len(state.step_outputs)} / {state.total_steps()}")

        m4.metric("Trace ID", trace_id[:8] + "…")



        if state.plan:

            with st.expander("Plan (planner output)", expanded=False):

                st.json(state.plan)



        st.markdown("### Final answer")

        st.markdown(_format_final_answer(state))



        if len(judge_scores) > 1:
            st.caption(f"Per-step judge scores: {', '.join(str(s) for s in judge_scores)}")

        st.markdown("### Audit trail (this run)")

        if trace_id in traces:

            _render_trace_detail(traces, trace_id, key_prefix="run-")

        else:

            st.info("Trace not found yet — click Reload in the sidebar.")



with history_tab:

    spans = load_spans(DEFAULT_LOG_PATH)

    traces = group_by_trace(spans)



    if not spans:

        st.info("No traces yet. Run a task in the **Run pipeline** tab.")

    else:

        summaries = [summarize_trace(traces[tid]) for tid in traces]

        summaries.sort(key=lambda s: s["started_at"], reverse=True)



        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total traces", len(summaries))

        col2.metric("Total spans", len(spans))

        passed_count = sum(1 for s in summaries if s["final_verdict"] == "pass")

        col3.metric("Passed", passed_count)

        col4.metric("Failed / other", len(summaries) - passed_count)



        table_rows = []

        for s in summaries:

            verdict = s["final_verdict"] or ("error" if s["has_error"] else "—")

            table_rows.append(

                {

                    "trace_id": s["trace_id"][:8] + "…",

                    "started": s["started_at"][:19],

                    "spans": s["span_count"],

                    "latency_ms": s["total_latency_ms"],

                    "pipeline": s["agents"],

                    "verdict": verdict,

                    "score": str(s["final_score"]) if s["final_score"] is not None else "—",

                }

            )

        st.dataframe(table_rows, use_container_width=True, hide_index=True)



        trace_ids = [s["trace_id"] for s in summaries]

        labels = [

            f"{s['trace_id'][:8]}… — {s['final_verdict'] or 'no verdict'} ({s['span_count']} spans)"

            for s in summaries

        ]



        default_index = 0

        last_id = st.session_state.get("last_trace_id")

        if last_id in trace_ids:

            default_index = trace_ids.index(last_id)



        st.subheader("Trace detail")

        selected = st.selectbox(

            "Select a trace",

            trace_ids,

            index=default_index,

            format_func=lambda tid: labels[trace_ids.index(tid)],

        )

        _render_trace_detail(traces, selected, key_prefix="hist-")



with guide_tab:

    guide_path = Path(__file__).resolve().parent.parent / "docs" / "INTERVIEW.md"

    if guide_path.exists():

        st.markdown(guide_path.read_text(encoding="utf-8"))

    else:

        st.warning("docs/INTERVIEW.md not found.")


