"""Tests for the PawPal+ agentic layer.

The LLM is mocked (no network) via a FakeClient, so these run offline and
deterministically. They cover: the fallback path, the happy LLM path, the
guardrail override, the revise loop, and schema validation.
"""

from config import Settings
from agent.planner import PawPalAgent
from agent.schemas import ValidationError, normalize_critique, normalize_tasks
from agent import fallback


def _settings(has_key: bool = False, max_iterations: int = 3) -> Settings:
    return Settings(
        gemini_api_key="test-key" if has_key else "",
        model="gemini-2.5-flash",
        max_iterations=max_iterations,
        max_tasks=20,
    )


class FakeClient:
    """Stand-in for GeminiClient that returns scripted JSON."""

    def __init__(self, plan_responses, critique_responses, available=True):
        self.available = available
        self._plans = list(plan_responses)
        self._critiques = list(critique_responses)
        self.plan_calls = 0
        self.critique_calls = 0

    def plan(self, system, prompt):
        self.plan_calls += 1
        return self._plans[min(self.plan_calls - 1, len(self._plans) - 1)]

    def critique(self, system, prompt):
        self.critique_calls += 1
        return self._critiques[min(self.critique_calls - 1, len(self._critiques) - 1)]


# --------------------------------------------------------------- schema tests
def test_normalize_tasks_clamps_and_drops_invalid():
    raw = [
        {"title": "Walk", "duration_minutes": 999, "priority": "URGENT", "category": "bogus"},
        {"title": "", "duration_minutes": 10, "priority": "high"},  # dropped: no title
        {"title": "Meds", "duration_minutes": "5", "priority": "high", "category": "health"},
    ]
    cleaned = normalize_tasks(raw, max_tasks=20)
    assert len(cleaned) == 2
    assert cleaned[0]["duration_minutes"] == 240  # clamped
    assert cleaned[0]["priority"] == "medium"  # coerced from unknown
    assert cleaned[0]["category"] == "care"  # coerced from unknown
    assert cleaned[1]["duration_minutes"] == 5


def test_normalize_tasks_rejects_non_list():
    try:
        normalize_tasks({"not": "a list"}, max_tasks=20)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_normalize_critique_shapes_output():
    result = normalize_critique({"ok": "yes", "issues": "one problem"})
    assert result["ok"] is True
    assert result["issues"] == ["one problem"]
    assert result["suggested_fixes"] == []


# ------------------------------------------------------------- fallback tests
def test_fallback_parser_extracts_known_tasks():
    tasks = fallback.parse_tasks("Dog needs a walk and his medication")
    titles = [t["title"] for t in tasks]
    assert any("Walk" in t for t in titles)
    assert any("Medication" in t for t in titles)


def test_fallback_never_returns_empty():
    tasks = fallback.parse_tasks("some unrelated text")
    assert len(tasks) >= 1


# ------------------------------------------------------------- agent behavior
def test_agent_fallback_mode_when_no_key():
    agent = PawPalAgent(settings=_settings(has_key=False), client=FakeClient([], [], available=False))
    result = agent.run("Dog needs a walk and meds", available_minutes=300)

    assert result.used_fallback is True
    assert result.day_plan is not None
    assert len(result.proposed_tasks) >= 1
    # Trace must contain all three phases.
    phases = {step.phase for step in result.trace}
    assert {"PLAN", "ACT", "CHECK"} <= phases


def test_agent_happy_path_converges_first_iteration():
    plan = [{"title": "Walk", "duration_minutes": 30, "priority": "high", "category": "exercise"}]
    critique = {"ok": True, "issues": [], "suggested_fixes": []}
    client = FakeClient([plan], [critique], available=True)

    agent = PawPalAgent(settings=_settings(has_key=True), client=client)
    result = agent.run("walk the dog", available_minutes=300)

    assert result.iterations == 1
    assert result.critique["ok"] is True
    assert result.used_fallback is False
    assert len(result.day_plan.scheduled_items) == 1


def test_guardrail_overrides_optimistic_llm():
    # Task needs 300 min but only 60 available -> it will not fit.
    plan = [{"title": "Marathon walk", "duration_minutes": 240, "priority": "high", "category": "exercise"}]
    # LLM lies and says everything is fine.
    critique = {"ok": True, "issues": [], "suggested_fixes": []}
    client = FakeClient([plan], [critique], available=True)

    agent = PawPalAgent(settings=_settings(has_key=True, max_iterations=1), client=client)
    result = agent.run("long walk", available_minutes=60)

    # Deterministic guardrail must flip the verdict to not-ok.
    assert result.critique["ok"] is False
    assert any("did not fit" in issue for issue in result.critique["issues"])


def test_agent_revises_then_converges():
    over_budget = [{"title": "Huge walk", "duration_minutes": 240, "priority": "high", "category": "exercise"}]
    fits = [{"title": "Short walk", "duration_minutes": 20, "priority": "high", "category": "exercise"}]
    # First critique flags a problem; guardrail also flips iter 1 anyway.
    critiques = [
        {"ok": False, "issues": ["too long"], "suggested_fixes": ["shorten"]},
        {"ok": True, "issues": [], "suggested_fixes": []},
    ]
    client = FakeClient([over_budget, fits], critiques, available=True)

    agent = PawPalAgent(settings=_settings(has_key=True, max_iterations=3), client=client)
    result = agent.run("walk the dog", available_minutes=60)

    assert result.iterations == 2
    assert result.critique["ok"] is True
    assert client.plan_calls == 2  # re-planned once
