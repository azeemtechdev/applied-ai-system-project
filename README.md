# PawPal+ — An Agentic Pet-Care Planning Assistant

## Original Project (Modules 1–3)

**PawPal+** began as a deterministic pet-care scheduler. Its original goal was to help a
busy pet owner stay consistent with daily care by turning a list of tasks (walks, feeding,
medication, grooming, enrichment) into an ordered, time-boxed daily plan. The Module 1–3
version could store owner and pet profiles, rank tasks by priority and duration, generate a
schedule that fit the owner's available time, detect time conflicts, handle recurring tasks,
and explain each plan — exposed through a Streamlit UI, a CLI demo, and a small pytest suite.

## Title and Summary

**PawPal+** is now a full **applied AI system** with an **agentic workflow**: an AI that can
**plan, act, and check its own work**. The owner describes their day in plain English
("I have 5 hours; my dog needs a walk, two feedings, and his meds"), and the agent extracts
structured tasks, schedules them, critiques its own plan, and revises — then a human approves,
edits, or rejects before anything is saved.

Why it matters: natural language is how people actually think about their day, but a language
model alone can't be trusted to do time arithmetic or respect a budget. PawPal+ splits the job
so the AI does the part it's good at (understanding language, judging quality) and a verified
engine does the part that must be correct (scheduling), making the result both easy to use and
trustworthy.

## Architecture Overview

The core design principle is the trust story:

> **The LLM (Gemini) does language and judgment. The deterministic `Scheduler` does the math.**

The agent runs a four-step loop:

1. **PLAN** *(Gemini)* — extract structured tasks from the owner's free text.
2. **ACT** *(deterministic engine)* — schedule those tasks with the existing `Scheduler`.
3. **CHECK** — deterministic guardrails (Did any high-priority task get dropped? Over budget?
   Time conflicts?) **plus** an LLM critique. The guardrails **override** the LLM: if the checker
   finds a problem, the plan is marked *needs revision* even if the model claimed it was fine.
4. **REVISE** — feed the critique back and try again, capped at 3 iterations.

Then a **human gate** in the UI requires **Approve / Edit / Reject** before any plan is committed.
Every step is written to `logs/pawpal.log`, and if Gemini is unavailable the system degrades to a
deterministic keyword parser so it always runs.

The full system diagram, component table, and data-flow explanation live in
[`docs/architecture.md`](docs/architecture.md).

```
Natural language ─► PLAN (Gemini) ─► schema guardrails ─► ACT (Scheduler)
                                                              │
                        ┌── revise (≤3) ◄── CHECK (guardrails + LLM critique)
                        ▼
             Human gate: Approve · Edit · Reject ─► committed plan + explanation
```

## Setup Instructions

Requires **Python 3.10+**.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Enable the Gemini-powered AI Planner
cp .env.example .env             # Windows: copy .env.example .env
# Paste a free-tier key from https://aistudio.google.com/apikey into GEMINI_API_KEY
```

> **No API key? It still works.** With no `GEMINI_API_KEY`, PawPal+ runs the AI Planner in a
> **deterministic fallback mode** (a keyword parser) so the whole system is reproducible offline.

Run it:

```bash
streamlit run app.py        # interactive UI (includes the AI Planner + human gate)
python agent_demo.py        # agentic Plan → Act → Check demo (CLI)
python main.py              # original deterministic scheduling demo (CLI)
python -m pytest -q         # test suite (runs offline; LLM is mocked)
```

## Sample Interactions

### Example 1 — Plan fits the budget (fallback mode, no key)

**Input:** *"My dog Biscuit needs a 30-minute morning walk, two feedings, and his medication.
My cat also needs grooming and some playtime."* (available time: 300 minutes)

**Output:**
```
[iter 1] PLAN   | Extracted 6 task(s): Walk (30m/high), Feeding (1) (10m/high),
                  Feeding (2) (10m/high), Medication (5m/high), Grooming (15m/medium),
                  Playtime (20m/low)
[iter 1] ACT    | Scheduled 6 item(s); guardrail findings: none
[iter 1] CHECK  | Self-check verdict: acceptable. Issues: none

SELF-CHECK VERDICT: ACCEPTABLE
Daily plan for Biscuit:
00:00 - 00:05 | Medication (5m) [priority: high]
00:05 - 00:15 | Feeding (1) (10m) [priority: high]
00:15 - 00:25 | Feeding (2) (10m) [priority: high]
00:25 - 00:55 | Walk (30m) [priority: high]
00:55 - 01:10 | Grooming (15m) [priority: medium]
01:10 - 01:30 | Playtime (20m) [priority: low]
Total scheduled: 90 minutes  |  Remaining time: 210 minutes
```

### Example 2 — Self-check catches an over-budget plan

**Input:** *"Dog needs a vet visit, a walk, grooming, and medication."* (available time: **45 minutes**)

**Output:**
```
[iter 1] PLAN   | Extracted 4 task(s): Walk (30m/high), Medication (5m/high),
                  Grooming (15m/medium), Vet visit (60m/high)
[iter 1] ACT    | Scheduled 2 item(s); guardrail findings:
                  1 high-priority task(s) did not fit: Vet visit.;
                  1 task(s) did not fit in the time budget: Grooming.
[iter 1] CHECK  | Self-check verdict: needs revision.

SELF-CHECK VERDICT: NEEDS REVISION
  issue: 1 high-priority task(s) did not fit: Vet visit.
  issue: 1 task(s) did not fit in the time budget: Grooming.

Daily plan for Biscuit:
00:00 - 00:05 | Medication (5m) [priority: high]
00:05 - 00:35 | Walk (30m) [priority: high]
Total scheduled: 35 minutes  |  Remaining time: 10 minutes
```
The agent honestly reports that the vet visit and grooming don't fit in 45 minutes instead of
silently dropping them — the deterministic guardrail drives the verdict.

### Example 3 — Human-in-the-loop gate (Streamlit UI)

1. In the **🤖 AI Planner** section, type: *"I have 4 hours; cat needs feeding twice, a brush, and playtime."*
2. Click **Plan with AI**. The app shows the Plan → Act → Check trace and the self-check verdict.
3. The proposed tasks appear in an editable table — change a duration or priority if you like.
4. Click **✅ Approve & commit** to save the tasks to the selected pet, or **❌ Reject** to retry.
   Nothing is committed until you approve.

## Design Decisions and Trade-offs

- **LLM for language, engine for math.** The single most important decision. The model never
  computes times or totals, so the AI can't invent time that isn't there. Trade-off: the schedule
  is only as smart as the greedy `Scheduler`, but it is always correct and explainable.
- **Deterministic guardrails override the LLM.** A self-critiquing model can be over-confident, so
  objective code checks (dropped high-priority tasks, over-budget, conflicts) have the final say.
  Trade-off: more code than trusting the model, but far more trustworthy.
- **Graceful fallback instead of a hard dependency.** With no key, a keyword parser keeps the loop
  running. Trade-off: the fallback is naive (e.g. it can misread a number as a task count), but it
  guarantees the project runs and tests reproducibly offline.
- **Human approval gate.** The AI proposes; the human disposes. Trade-off: one extra click, but it
  keeps a person accountable for what gets scheduled.
- **Capped loop + schema clamping.** Iterations are capped at 3 and every LLM field is validated and
  clamped (duration 1–240, known priorities, task-count limit) so bad output can't run away or crash.
- **Isolated `agent/` package.** The AI layer is fully separate from the verified core in
  `pawpal_system.py`, which was reused almost unchanged (only a `Task.from_dict` helper was added).

## Testing Summary

- **Suite:** `python -m pytest -q` → **12 passed** (3 original scheduler tests + 9 new agent tests).
- **What worked:** All agent tests run **offline with a mocked LLM**, so they're fast and
  deterministic. They cover the fallback path, happy-path convergence on the first iteration, the
  revise loop (re-plan then converge), schema validation/clamping of bad LLM output, and — most
  importantly — the **guardrail override**: a test feeds an unfittable task plus a lying LLM that
  says "ok", and asserts the deterministic check flips the verdict to *needs revision*.
- **What didn't (and how it was handled):** The deterministic fallback parser is naive — it can
  misinterpret a number near a keyword (e.g. "60 minute vet visit" briefly parsed as three vet
  visits). This is a known limitation of the offline parser, not the Gemini path; the guardrails
  still caught the resulting over-budget plan, which is exactly what they're for.
- **What I learned:** Testing an AI system is mostly about testing the *guardrails around* the AI.
  Mocking the LLM made the agent's control flow (loop, revision, override) fully testable without a
  network, which is where the real correctness risk lives.

## Reflection

A short reflection on what this project taught me lives here, but the **graded responsible-AI
reflection** — how I collaborated with AI, one helpful and one flawed AI suggestion, and the
system's limitations — is in [`model_card.md`](model_card.md).

## Project Structure

```
pawpal_system.py      # deterministic core: Owner, Pet, Task, Scheduler, DayPlan, ...
agent/
  planner.py          # PawPalAgent — the Plan → Act → Check → Revise loop
  llm_client.py       # Gemini wrapper (JSON output, retry, graceful degrade)
  schemas.py          # validate + clamp all LLM output (guardrail)
  prompts.py          # versioned PLAN + CRITIQUE prompts
  fallback.py         # deterministic keyword parser (no-key mode)
config.py             # loads .env: key, model, loop/task caps
logging_config.py     # audit log → logs/pawpal.log
app.py                # Streamlit UI + AI Planner + human Approve/Edit/Reject gate
agent_demo.py         # CLI demo of the agentic loop
main.py               # original deterministic scheduling demo
docs/architecture.md  # system diagram + data flow
tests/                # test_pawpal.py (core) + test_agent.py (agent, mocked LLM)
```
