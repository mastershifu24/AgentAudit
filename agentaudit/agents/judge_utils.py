"""Normalize judge verdicts so pass/fail matches the assigned step."""

SCOPE_OK_PHRASES = (
    "within the expected scope",
    "within scope",
    "not required for the assigned step",
    "was only to",
    "only list",
    "without explanations",
)


def normalize_verdict(verdict: dict) -> dict:
    issues = list(verdict.get("issues") or [])
    score = verdict.get("score", 0)
    passed = bool(verdict.get("pass"))

    # Judge praised the output in issues but still failed — treat as pass.
    if issues and not passed:
        joined = " ".join(issues).lower()
        if any(phrase in joined for phrase in SCOPE_OK_PHRASES):
            if "scope creep" not in joined and "jumped ahead" not in joined:
                passed = True
                issues = []

    # No real issues and reasonable score → pass.
    if not issues and score >= 70:
        passed = True

    if passed:
        issues = []
        verdict["suggestion"] = ""

    verdict["pass"] = passed
    verdict["issues"] = issues
    return verdict
