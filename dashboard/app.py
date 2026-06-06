"""
AgentAudit trace viewer.

Run from project root:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from agentaudit.trace.reader import group_by_trace, load_spans, summarize_trace
from agentaudit.trace.store import DEFAULT_LOG_PATH

st.set_page_config(page_title="AgentAudit", page_icon="🔍", layout="wide")

st.title("AgentAudit")
st.caption("LLM trace viewer — inspect multi-agent runs, judge verdicts, and retries")

log_path = DEFAULT_LOG_PATH
spans = load_spans(log_path)
traces = group_by_trace(spans)

if not spans:
    st.info(f"No spans yet. Run `python -m demo.minimal_demo` first.")
    st.stop()

summaries = [summarize_trace(traces[tid]) for tid in traces]
summaries.sort(key=lambda s: s["started_at"], reverse=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total traces", len(summaries))
col2.metric("Total spans", len(spans))
passed = sum(1 for s in summaries if s["final_verdict"] == "pass")
col3.metric("Passed", passed)
col4.metric("Failed / other", len(summaries) - passed)

st.subheader("Recent runs")

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

st.dataframe(table_rows, width="stretch", hide_index=True)

trace_ids = [s["trace_id"] for s in summaries]
labels = [
    f"{s['trace_id'][:8]}… — {s['final_verdict'] or 'no verdict'} ({s['span_count']} spans)"
    for s in summaries
]

st.subheader("Trace detail")
selected = st.selectbox("Select a trace", trace_ids, format_func=lambda tid: labels[trace_ids.index(tid)])

selected_spans = traces[selected]
summary = summarize_trace(selected_spans)

detail_col1, detail_col2, detail_col3 = st.columns(3)
detail_col1.write(f"**Trace ID:** `{summary['trace_id']}`")
detail_col2.write(f"**Final verdict:** `{summary['final_verdict'] or '—'}`")
detail_col3.write(f"**Total latency:** {summary['total_latency_ms']} ms")

st.write(f"**Pipeline:** {summary['agents']}")

for i, span in enumerate(selected_spans, start=1):
    agent = span["agent_name"]
    status = span.get("status", "ok")
    verdict = span.get("verdict")
    title = f"{i}. {agent} — {status}"
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

        st.text_area("Input", span.get("input", ""), height=120, key=f"in-{span['span_id']}")
        st.text_area("Output", span.get("output", ""), height=200, key=f"out-{span['span_id']}")

st.sidebar.markdown("### Refresh")
if st.sidebar.button("Reload traces"):
    st.rerun()

st.sidebar.markdown(f"Reading `{log_path}`")
