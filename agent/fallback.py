"""Deterministic fallback used when Gemini is unavailable.

Keeps the whole Plan-Act-Check loop functional with no API key (or when a
call fails), so the system always runs reproducibly. This is a keyword/regex
parser — intentionally simple and transparent, not an LLM substitute.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# keyword -> (canonical title, default duration, priority, category)
_KEYWORD_MAP = {
    "walk": ("Walk", 30, "high", "exercise"),
    "feed": ("Feeding", 10, "high", "nutrition"),
    "feeding": ("Feeding", 10, "high", "nutrition"),
    "meal": ("Feeding", 10, "high", "nutrition"),
    "breakfast": ("Breakfast feeding", 10, "high", "nutrition"),
    "dinner": ("Dinner feeding", 10, "high", "nutrition"),
    "med": ("Medication", 5, "high", "health"),
    "medication": ("Medication", 5, "high", "health"),
    "medicine": ("Medication", 5, "high", "health"),
    "pill": ("Medication", 5, "high", "health"),
    "groom": ("Grooming", 15, "medium", "grooming"),
    "grooming": ("Grooming", 15, "medium", "grooming"),
    "brush": ("Brushing", 15, "medium", "grooming"),
    "bath": ("Bath", 20, "medium", "grooming"),
    "play": ("Playtime", 20, "low", "enrichment"),
    "playtime": ("Playtime", 20, "low", "enrichment"),
    "train": ("Training", 20, "medium", "enrichment"),
    "vet": ("Vet visit", 60, "high", "health"),
}

# number words -> count, for phrases like "two feeds"
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
}

# match an explicit duration near a keyword, e.g. "30-min", "45 minutes"
_DURATION_RE = re.compile(r"(\d{1,3})\s*[- ]?\s*(?:min|minute)", re.IGNORECASE)


def _count_before(text: str, keyword: str) -> int:
    """Return a small multiplier if a number precedes the keyword (max 3)."""
    match = re.search(rf"(\d+|{'|'.join(_NUMBER_WORDS)})\s+\w*\s*{keyword}", text)
    if not match:
        return 1
    token = match.group(1)
    count = _NUMBER_WORDS.get(token, None)
    if count is None:
        try:
            count = int(token)
        except ValueError:
            count = 1
    return max(1, min(3, count))


def parse_tasks(nl_text: str) -> List[Dict[str, Any]]:
    """Extract care tasks from free text via keyword matching.

    Returns raw dicts in the same shape the LLM produces, so the same schema
    validation applies to both paths.
    """
    text = nl_text.lower()
    tasks: List[Dict[str, Any]] = []
    seen_titles: set[str] = set()

    # Any explicit duration in the sentence is used for the first matched task.
    duration_hint = _DURATION_RE.search(text)
    hinted_minutes = int(duration_hint.group(1)) if duration_hint else None
    hint_used = False

    for keyword, (title, default_minutes, priority, category) in _KEYWORD_MAP.items():
        if keyword not in text:
            continue

        count = _count_before(text, keyword)
        for index in range(count):
            minutes = default_minutes
            if hinted_minutes is not None and not hint_used:
                minutes = hinted_minutes
                hint_used = True

            entry_title = title if count == 1 else f"{title} ({index + 1})"
            if entry_title in seen_titles:
                continue
            seen_titles.add(entry_title)

            tasks.append(
                {
                    "title": entry_title,
                    "duration_minutes": minutes,
                    "priority": priority,
                    "category": category,
                }
            )

    if not tasks:
        # Never return empty: emit a single generic care task.
        tasks.append(
            {
                "title": "General care",
                "duration_minutes": 15,
                "priority": "medium",
                "category": "care",
            }
        )
    return tasks


def critique(guardrail_findings: List[str]) -> Dict[str, Any]:
    """Deterministic stand-in for the LLM critique, driven by guardrails."""
    ok = len(guardrail_findings) == 0
    return {
        "ok": ok,
        "issues": list(guardrail_findings),
        "suggested_fixes": (
            [] if ok else ["Reduce durations or drop low-priority tasks to fit the time budget."]
        ),
    }
