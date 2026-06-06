import json
import re
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

from agentaudit.trace.context import (
    get_last_span_id,
    get_parent_span_id,
    get_trace_id,
    reset_parent_span_id,
    set_last_span_id,
    set_parent_span_id,
)
from agentaudit.trace.store import append_span

F = TypeVar("F", bound=Callable[..., Any])


def _extract_prompt(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    if "prompt" in kwargs:
        return str(kwargs["prompt"])
    if len(args) >= 2:
        return "\n---\n".join(str(arg) for arg in args)
    if args:
        return str(args[0])
    return ""


def _extract_token_counts(result: Any) -> tuple[int | None, int | None]:
    usage = getattr(result, "usage_metadata", None)
    if usage is None:
        return None, None
    tokens_in = getattr(usage, "prompt_token_count", None)
    tokens_out = getattr(usage, "candidates_token_count", None)
    return tokens_in, tokens_out


def _extract_output_text(result: Any) -> str:
    text = getattr(result, "text", None)
    if text is not None:
        return text
    return str(result)


def _judge_span_fields(agent_name: str, output: str, status: str) -> dict[str, Any]:
    if agent_name != "judge" or status != "ok":
        return {}
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return {}
    if "pass" not in data:
        return {}
    fields: dict[str, Any] = {
        "verdict": "pass" if data["pass"] else "fail",
    }
    if "score" in data:
        fields["score"] = data["score"]
    return fields


def trace_llm(agent_name: str) -> Callable[[F], F]:
    """Wrap an LLM call and append a structured span to traces.jsonl."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_id = str(uuid.uuid4())
            parent_span_id = get_parent_span_id() or get_last_span_id()
            parent_token = set_parent_span_id(span_id)

            prompt = _extract_prompt(args, kwargs)
            started = time.perf_counter()
            status = "ok"
            result: Any = None
            output = ""
            tokens_in: int | None = None
            tokens_out: int | None = None

            try:
                result = fn(*args, **kwargs)
                tokens_in, tokens_out = _extract_token_counts(result)
                output = _extract_output_text(result)
                return result
            except Exception as exc:
                status = "error"
                output = str(exc)
                raise
            finally:
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                span = {
                    "trace_id": get_trace_id(),
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "agent_name": agent_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "input": prompt,
                    "output": output,
                    "latency_ms": latency_ms,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "status": status,
                }
                span.update(_judge_span_fields(agent_name, output, status))
                append_span(span)
                set_last_span_id(span_id)
                reset_parent_span_id(parent_token)

        return wrapper  # type: ignore[return-value]

    return decorator
