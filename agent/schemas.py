"""Validation + normalization for LLM output.

The LLM is untrusted input. Everything it returns passes through here before
touching the scheduler: fields are clamped to safe ranges, unknown priorities
are coerced, and malformed items are dropped. This is a guardrail, not a
convenience — it guarantees the deterministic core only ever sees valid data.
"""

from __future__ import annotations

from typing import Any, Dict, List

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_CATEGORIES = {
    "exercise",
    "nutrition",
    "health",
    "grooming",
    "enrichment",
    "care",
}

MIN_DURATION = 1
MAX_DURATION = 240


class ValidationError(ValueError):
    """Raised when LLM output cannot be repaired into a usable structure."""


def _clamp_duration(value: Any) -> int:
    """Coerce a duration to an int within [MIN_DURATION, MAX_DURATION]."""
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"duration_minutes not an int: {value!r}")
    return max(MIN_DURATION, min(MAX_DURATION, minutes))


def _normalize_priority(value: Any) -> str:
    """Map arbitrary priority text to a valid level, defaulting to medium."""
    text = str(value or "").strip().lower()
    return text if text in VALID_PRIORITIES else "medium"


def _normalize_category(value: Any) -> str:
    """Map arbitrary category text to a known category, defaulting to care."""
    text = str(value or "").strip().lower()
    return text if text in VALID_CATEGORIES else "care"


def normalize_tasks(raw_tasks: Any, max_tasks: int) -> List[Dict[str, Any]]:
    """Validate and clamp a list of raw task dicts from the LLM.

    Invalid individual entries are skipped rather than crashing the run. The
    overall structure must be a list, or ValidationError is raised so the
    caller can retry or fall back.
    """
    if not isinstance(raw_tasks, list):
        raise ValidationError(f"expected a list of tasks, got {type(raw_tasks).__name__}")

    cleaned: List[Dict[str, Any]] = []
    for entry in raw_tasks:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        try:
            duration = _clamp_duration(entry.get("duration_minutes"))
        except ValidationError:
            continue
        cleaned.append(
            {
                "title": title,
                "duration_minutes": duration,
                "priority": _normalize_priority(entry.get("priority")),
                "category": _normalize_category(entry.get("category")),
            }
        )
        if len(cleaned) >= max_tasks:
            break

    if not cleaned:
        raise ValidationError("no valid tasks after normalization")
    return cleaned


def normalize_critique(raw: Any) -> Dict[str, Any]:
    """Validate a critique dict from the LLM into {ok, issues, suggested_fixes}."""
    if not isinstance(raw, dict):
        raise ValidationError(f"expected a critique object, got {type(raw).__name__}")

    ok = bool(raw.get("ok", False))
    issues = raw.get("issues", [])
    fixes = raw.get("suggested_fixes", [])

    if not isinstance(issues, list):
        issues = [str(issues)]
    if not isinstance(fixes, list):
        fixes = [str(fixes)]

    return {
        "ok": ok,
        "issues": [str(i) for i in issues],
        "suggested_fixes": [str(f) for f in fixes],
    }
