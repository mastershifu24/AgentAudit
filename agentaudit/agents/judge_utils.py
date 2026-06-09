"""Normalize judge verdicts so pass/fail matches the assigned step."""

import re

SCOPE_OK_PHRASES = (
    "within the expected scope",
    "within scope",
    "not required for the assigned step",
    "was only to",
    "only list",
    "without explanations",
)

LIST_ONLY_HINTS = ("identify", "list", "name three", "name 3", "research three", "pick three")
EXPLAIN_HINTS = ("explain", "sentence", "describe", "why each", "one line each")


def step_expects_list_only(assigned_step: str) -> bool:
    step = assigned_step.lower()
    if not any(hint in step for hint in LIST_ONLY_HINTS):
        return False
    return not any(hint in step for hint in EXPLAIN_HINTS)


def has_explanations(worker_output: str) -> bool:
    """Detect explanations on a list-only step (not plain '1. Item' numbering)."""
    for line in worker_output.splitlines():
        line = line.strip()
        if not line:
            continue
        body = re.sub(r"^[\d]+[\.\)]\s*", "", line)
        body = re.sub(r"^[-*•]\s*", "", body).strip()
        body = re.sub(r"^\*\*|\*\*$", "", body).strip()

        if ":" in body:
            after_colon = body.split(":", 1)[1].strip()
            if len(after_colon) > 20:
                return True

        if len(body) > 55:
            return True

    return False


def normalize_verdict(
    verdict: dict,
    assigned_step: str = "",
    worker_output: str = "",
) -> dict:
    issues = list(verdict.get("issues") or [])
    score = verdict.get("score", 0)
    passed = bool(verdict.get("pass"))

    if assigned_step and worker_output and step_expects_list_only(assigned_step):
        if has_explanations(worker_output):
            passed = False
            if not issues:
                issues = ["Worker added explanations on a list-only step (scope creep)."]
            verdict["suggestion"] = (
                "List the items only — no explanations until the assigned step asks for them."
            )
            score = min(score, 40) if score else 40

    if issues and not passed:
        joined = " ".join(issues).lower()
        if any(phrase in joined for phrase in SCOPE_OK_PHRASES):
            if "scope creep" not in joined and "jumped ahead" not in joined:
                passed = True
                issues = []

    if not issues and score >= 70 and not (
        assigned_step and worker_output and step_expects_list_only(assigned_step) and has_explanations(worker_output)
    ):
        passed = True

    if passed and score < 1:
        score = 85

    if passed:
        issues = []
        verdict["suggestion"] = ""

    verdict["pass"] = passed
    verdict["issues"] = issues
    verdict["score"] = score
    return verdict
