"""The PawPal+ agent: a Plan-Act-Check loop.

PLAN   - turn the owner's natural-language description into structured tasks
         (Gemini, or a deterministic fallback parser).
ACT    - schedule those tasks with the existing deterministic ``Scheduler``.
CHECK  - run deterministic guardrails (what got dropped? conflicts?) and an
         LLM critique; guardrail findings always override the LLM's verdict.
REVISE - if the plan is not acceptable, feed the critique back and try again,
         capped at ``max_iterations``.

The LLM never computes times or totals; that stays in the verified core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from config import Settings, get_settings
from logging_config import get_logger
from pawpal_system import (
    DayPlan,
    Owner,
    Pet,
    Scheduler,
    SchedulingConstraints,
    Task,
)
from agent import fallback, prompts
from agent.llm_client import GeminiClient, LLMError
from agent.schemas import ValidationError, normalize_critique, normalize_tasks


@dataclass
class AgentStep:
    """One recorded step in the agent's reasoning trace."""

    phase: str  # PLAN | ACT | CHECK | REVISE
    iteration: int
    detail: str


@dataclass
class AgentResult:
    """Everything the agent produced, for display and human review."""

    proposed_tasks: List[Task] = field(default_factory=list)
    day_plan: DayPlan | None = None
    critique: dict = field(default_factory=dict)
    guardrail_findings: List[str] = field(default_factory=list)
    iterations: int = 0
    used_fallback: bool = False
    trace: List[AgentStep] = field(default_factory=list)


class PawPalAgent:
    """Runs the Plan-Act-Check loop over natural-language care requests."""

    def __init__(self, settings: Settings | None = None, client: GeminiClient | None = None):
        self.settings = settings or get_settings()
        self.client = client if client is not None else GeminiClient(self.settings)
        self.logger = get_logger()

    def run(
        self,
        nl_text: str,
        pet: Pet | None = None,
        owner: Owner | None = None,
        available_minutes: int = 480,
    ) -> AgentResult:
        """Execute the loop and return the full trace + final plan."""
        owner = owner or Owner(name="Owner", available_time_minutes=available_minutes)
        pet = pet or Pet(name="your pet", species="pet")
        pet_context = pet.get_summary()

        result = AgentResult()
        revision_note = ""

        self.logger.info(
            "Agent run start | fallback_mode=%s | available_minutes=%d",
            not self.client.available,
            available_minutes,
        )

        for iteration in range(1, self.settings.max_iterations + 1):
            result.iterations = iteration

            # --- PLAN ---
            task_dicts, plan_fallback = self._plan(
                nl_text, pet_context, available_minutes, revision_note
            )
            result.used_fallback = result.used_fallback or plan_fallback
            proposed_tasks = [Task.from_dict(d, pet=pet) for d in task_dicts]
            result.proposed_tasks = proposed_tasks
            summary = ", ".join(f"{t.title} ({t.duration_minutes}m/{t.priority})" for t in proposed_tasks)
            self._record(result, "PLAN", iteration, f"Extracted {len(proposed_tasks)} task(s): {summary}")

            # --- ACT ---
            day_plan, findings, scheduler = self._act(proposed_tasks, owner, pet, available_minutes)
            result.day_plan = day_plan
            result.guardrail_findings = findings
            self._record(
                result,
                "ACT",
                iteration,
                f"Scheduled {len(day_plan.scheduled_items)} item(s); guardrail findings: "
                + ("; ".join(findings) if findings else "none"),
            )

            # --- CHECK ---
            critique, check_fallback = self._check(proposed_tasks, day_plan, findings, available_minutes)
            result.used_fallback = result.used_fallback or check_fallback
            result.critique = critique
            verdict = "acceptable" if critique["ok"] else "needs revision"
            self._record(
                result,
                "CHECK",
                iteration,
                f"Self-check verdict: {verdict}. Issues: "
                + ("; ".join(critique["issues"]) if critique["issues"] else "none"),
            )

            if critique["ok"]:
                self.logger.info("Agent converged at iteration %d.", iteration)
                break

            # Fallback planning is deterministic: re-running yields the same
            # tasks, so revising would loop pointlessly. Stop early.
            if plan_fallback:
                self._record(result, "REVISE", iteration, "Fallback mode: skipping revision (deterministic).")
                break

            if iteration < self.settings.max_iterations:
                revision_note = (
                    "Your previous plan had these problems: "
                    + "; ".join(critique["issues"])
                    + ". Produce a corrected task list that fits the time budget."
                )
                self._record(result, "REVISE", iteration, "Feeding critique back into next PLAN.")

        self.logger.info(
            "Agent run end | iterations=%d | used_fallback=%s | ok=%s",
            result.iterations,
            result.used_fallback,
            result.critique.get("ok"),
        )
        return result

    # ------------------------------------------------------------------ PLAN
    def _plan(self, nl_text, pet_context, available_minutes, revision_note):
        """Return (validated task dicts, used_fallback)."""
        if self.client.available:
            prompt = prompts.build_plan_prompt(nl_text, pet_context, available_minutes, revision_note)
            try:
                raw = self.client.plan(prompts.PLAN_SYSTEM, prompt)
                return normalize_tasks(raw, self.settings.max_tasks), False
            except (LLMError, ValidationError) as exc:
                self.logger.warning("PLAN via LLM failed (%s); using fallback parser.", exc)

        raw = fallback.parse_tasks(nl_text)
        return normalize_tasks(raw, self.settings.max_tasks), True

    # ------------------------------------------------------------------- ACT
    def _act(self, tasks, owner, pet, available_minutes):
        """Schedule tasks and compute deterministic guardrail findings."""
        constraints = SchedulingConstraints(
            available_minutes=available_minutes,
            max_tasks=len(tasks),
        )
        scheduler = Scheduler(owner=owner, pet=pet, tasks=tasks, constraints=constraints)
        day_plan = scheduler.generate_schedule()

        scheduled_titles = {item.task.title for item in day_plan.scheduled_items if item.task}
        unscheduled = [t for t in tasks if t.title not in scheduled_titles]
        unscheduled_high = [t for t in unscheduled if t.get_priority_score() == 3]

        findings: List[str] = []
        if unscheduled_high:
            names = ", ".join(t.title for t in unscheduled_high)
            findings.append(f"{len(unscheduled_high)} high-priority task(s) did not fit: {names}.")
        other_unscheduled = [t for t in unscheduled if t.get_priority_score() != 3]
        if other_unscheduled:
            names = ", ".join(t.title for t in other_unscheduled)
            findings.append(f"{len(other_unscheduled)} task(s) did not fit in the time budget: {names}.")

        findings.extend(scheduler.detect_conflicts())
        return day_plan, findings, scheduler

    # ----------------------------------------------------------------- CHECK
    def _check(self, tasks, day_plan, findings, available_minutes):
        """Return (critique dict, used_fallback). Guardrails override the LLM."""
        used_fallback = False

        if self.client.available:
            plan_summary = day_plan.explain_plan()
            prompt = prompts.build_critique_prompt(
                plan_summary, "\n".join(findings), available_minutes
            )
            try:
                raw = self.client.critique(prompts.CRITIQUE_SYSTEM, prompt)
                critique = normalize_critique(raw)
            except (LLMError, ValidationError) as exc:
                self.logger.warning("CHECK via LLM failed (%s); using deterministic critique.", exc)
                critique = fallback.critique(findings)
                used_fallback = True
        else:
            critique = fallback.critique(findings)
            used_fallback = True

        # Guardrail override: objective findings always force a failing verdict
        # and are merged into the issue list, no matter what the LLM claimed.
        if findings:
            critique["ok"] = False
            for finding in findings:
                if finding not in critique["issues"]:
                    critique["issues"].append(finding)

        return critique, used_fallback

    # --------------------------------------------------------------- helpers
    def _record(self, result: AgentResult, phase: str, iteration: int, detail: str) -> None:
        """Append a step to the trace and log it."""
        result.trace.append(AgentStep(phase=phase, iteration=iteration, detail=detail))
        self.logger.info("[iter %d] %-6s | %s", iteration, phase, detail)
