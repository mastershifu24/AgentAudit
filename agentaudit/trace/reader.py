import json
import re
from pathlib import Path
from typing import Any

from agentaudit.trace.store import DEFAULT_LOG_PATH


def judge_scores_from_spans(spans: list[dict[str, Any]]) -> list[int]:
    """Extract judge scores from span fields or verdict JSON in output."""
    scores: list[int] = []
    for span in spans:
        if span.get("agent_name") != "judge":
            continue
        if span.get("score") is not None:
            scores.append(int(span["score"]))
            continue
        match = re.search(r"\{.*\}", span.get("output", ""), re.DOTALL)
        if not match:
            continue
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            continue
        if "score" in data:
            scores.append(int(data["score"]))
    return scores


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
    errors = [s for s in spans if s.get("status") == "error"]
    judge_scores = judge_scores_from_spans(spans)
    all_judges_passed = bool(judge_spans) and all(s.get("verdict") == "pass" for s in judge_spans)

    return {
        "trace_id": spans[0]["trace_id"],
        "started_at": spans[0]["timestamp"],
        "span_count": len(spans),
        "total_latency_ms": round(sum(s.get("latency_ms") or 0 for s in spans), 2),
        "agents": " → ".join(s["agent_name"] for s in spans),
        "final_verdict": "pass" if all_judges_passed else ("fail" if judge_spans else None),
        "final_score": min(judge_scores) if judge_scores else None,
        "judge_scores": judge_scores,
        "has_error": bool(errors),
    }
