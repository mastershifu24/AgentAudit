import uuid
from contextvars import ContextVar

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_parent_span_id: ContextVar[str | None] = ContextVar("parent_span_id", default=None)
_last_span_id: ContextVar[str | None] = ContextVar("last_span_id", default=None)


def init_trace() -> str:
    trace_id = str(uuid.uuid4())
    _trace_id.set(trace_id)
    _parent_span_id.set(None)
    _last_span_id.set(None)
    return trace_id


def get_trace_id() -> str:
    trace_id = _trace_id.get()
    if trace_id is None:
        trace_id = init_trace()
    return trace_id


def get_parent_span_id() -> str | None:
    return _parent_span_id.get()


def set_parent_span_id(span_id: str | None) -> object:
    return _parent_span_id.set(span_id)


def reset_parent_span_id(token: object) -> None:
    _parent_span_id.reset(token)


def get_last_span_id() -> str | None:
    return _last_span_id.get()


def set_last_span_id(span_id: str) -> None:
    _last_span_id.set(span_id)
