"""Web search for worker grounding — free metasearch via ddgs (no API key)."""

import os
import re

from agentaudit.trace import trace_llm

_PASTED_SOURCE_MIN_LEN = 1200


def is_web_search_enabled() -> bool:
    return os.getenv("AGENTAUDIT_WEB_SEARCH", "true").lower() in ("1", "true", "yes")


def should_search_task(task: str) -> bool:
    if not is_web_search_enabled():
        return False
    stripped = task.strip()
    if len(stripped) >= _PASTED_SOURCE_MIN_LEN:
        return False
    lower = stripped.lower()
    creative_only = bool(
        re.search(r"\b(write|poem|story|joke|haiku|rap lyrics)\b", lower)
    )
    factual = bool(
        re.search(
            r"\bresearch|find|compare|latest|job|role|company|skills|requirements|"
            r"who is|what is|how does|summarize|explain\b",
            lower,
        )
    )
    if creative_only and not factual:
        return False
    return True


def build_search_query(task: str) -> str:
    """Compact query from the user task (first line, trimmed)."""
    line = task.strip().splitlines()[0].strip()
    line = re.sub(r"\s+", " ", line)
    return line[:140] if len(line) > 140 else line


def _format_results(results: list[dict]) -> str:
    blocks: list[str] = []
    for i, hit in enumerate(results, start=1):
        title = (hit.get("title") or "").strip()
        href = (hit.get("href") or hit.get("url") or "").strip()
        body = (hit.get("body") or hit.get("snippet") or "").strip()
        if not title and not body:
            continue
        header = f"[{i}] {title}"
        if href:
            header += f" ({href})"
        blocks.append(f"{header}\n{body}" if body else header)
    return "\n\n".join(blocks)


@trace_llm(agent_name="web_search")
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web and return formatted snippets for the worker prompt."""
    from ddgs import DDGS

    hits = list(DDGS().text(query, max_results=max_results, backend="auto"))
    return _format_results(hits)


def fetch_task_search_context(task: str) -> str:
    """Run one search per pipeline when appropriate. Returns '' on skip or failure."""
    if not should_search_task(task):
        return ""
    query = build_search_query(task)
    if not query:
        return ""
    try:
        return search_web(query)
    except Exception:
        return ""
