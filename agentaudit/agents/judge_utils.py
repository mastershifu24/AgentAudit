"""Normalize judge verdicts — surgical fixes only when the step explicitly constrains format."""

import re

# Step text must contain one of these — never inferred from vague words like "list" or "research".
LIST_ONLY_MARKERS = (
    "titles only",
    "names only",
    "name only",
    "list only",
    "no explanations",
    "without explanations",
    "no description",
    "no detail",
)


def step_expects_explanations(assigned_step: str) -> bool:
    step = assigned_step.lower()
    return bool(
        re.search(
            r"\bexplain|\bsummarize\b|\bdescribe\b|\bone sentence\b|"
            r"\bbrief explanation\b|\bdetailing\b|\bimportance\b",
            step,
        )
    )


def step_explicitly_list_only(assigned_step: str) -> bool:
    """True only when the planner step explicitly forbids explanations."""
    if step_expects_explanations(assigned_step):
        return False
    step = assigned_step.lower()
    return any(marker in step for marker in LIST_ONLY_MARKERS)


def _item_lines(worker_output: str) -> list[str]:
    lines: list[str] = []
    for line in worker_output.splitlines():
        line = line.strip()
        if not line:
            continue
        body = re.sub(r"^[\d]+[\.\)]\s*", "", line)
        body = re.sub(r"^[-*•]\s*", "", body).strip()
        body = re.sub(r"^\*\*|\*\*$", "", body).strip()
        if body:
            lines.append(body)
    return lines


def has_explanations(worker_output: str) -> bool:
    """Detect per-item explanations (not plain '1. Item' numbering)."""
    for body in _item_lines(worker_output):
        if ":" in body:
            after_colon = body.split(":", 1)[1].strip()
            if len(after_colon) > 20:
                return True
        if len(body) > 55:
            return True
        if " and " in body.lower() and len(body) > 35:
            return True
    return False


def looks_like_clean_list(worker_output: str, min_items: int = 2) -> bool:
    """Short name-only lines with no explanation markers."""
    lines = _item_lines(worker_output)
    if len(lines) < min_items:
        return False
    return all(len(line) <= 55 and ":" not in line for line in lines)


def normalize_verdict(
    verdict: dict,
    assigned_step: str = "",
    worker_output: str = "",
) -> dict:
    issues = list(verdict.get("issues") or [])
    score = verdict.get("score", 0)
    passed = bool(verdict.get("pass"))

    if not assigned_step or not worker_output:
        verdict["pass"] = passed
        verdict["issues"] = issues
        verdict["score"] = score
        return verdict

    if step_explicitly_list_only(assigned_step):
        if has_explanations(worker_output):
            passed = False
            if not issues:
                issues = ["Worker added explanations on a list-only step (scope creep)."]
            verdict["suggestion"] = (
                "List the items only — no explanations until the assigned step asks for them."
            )
            score = min(score, 40) if score else 40
        elif looks_like_clean_list(worker_output):
            passed = True
            score = max(score, 85)
            issues = []
            verdict["suggestion"] = ""

    elif step_expects_explanations(assigned_step):
        if not has_explanations(worker_output):
            passed = False
            if not issues:
                issues = ["Step requires explanations but worker only listed items."]
            verdict["suggestion"] = "Add a clear one-sentence explanation for each item."
            score = min(score, 40) if score else 40
        elif has_explanations(worker_output):
            passed = True
            score = max(score, 85)
            issues = []
            verdict["suggestion"] = ""

    if passed:
        issues = []
        verdict["suggestion"] = ""
        if score < 1:
            score = 85

    verdict["pass"] = passed
    verdict["issues"] = issues
    verdict["score"] = score
    return verdict
