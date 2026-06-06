import json
from pathlib import Path
from typing import Any

from agentaudit.trace.store import DEFAULT_LOG_PATH


def load_spans(log_path: Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    spans: list[dict[str, Any]] = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                spans.append(json.loads(line))
    return spans


def group_by_trace(spans: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    traces: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        trace_id = span["trace_id"]
        traces.setdefault(trace_id, []).append(span)
    for trace_id in traces:
        traces[trace_id].sort(key=lambda s: s["timestamp"])
    return traces


def summarize_trace(spans: list[dict[str, Any]]) -> dict[str, Any]:
    judge_spans = [s for s in spans if s.get("agent_name") == "judge"]
    final_judge = judge_spans[-1] if judge_spans else None
    errors = [s for s in spans if s.get("status") == "error"]

    return {
        "trace_id": spans[0]["trace_id"],
        "started_at": spans[0]["timestamp"],
        "span_count": len(spans),
        "total_latency_ms": round(sum(s.get("latency_ms") or 0 for s in spans), 2),
        "agents": " → ".join(s["agent_name"] for s in spans),
        "final_verdict": final_judge.get("verdict") if final_judge else None,
        "final_score": final_judge.get("score") if final_judge else None,
        "has_error": bool(errors),
    }
