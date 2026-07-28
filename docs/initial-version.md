# PawPal+ — Initial Version

## The Idea

PawPal+ is a **pet care planning assistant**. A busy pet owner struggles to stay
consistent with daily pet care — walks, feeding, medication, grooming, enrichment.
PawPal+ takes the owner's tasks and available time and produces a clear daily plan,
then explains *why* it chose that plan.

The goal: turn a messy list of "things my pet needs" into an ordered, time-boxed
schedule the owner can actually follow.

## What It Does

- **Track owner + pet info** — owner name, preferences, and available time per day;
  one or more pets, each with its own profile (species, breed, age) and care notes.
- **Manage care tasks** — each task has a title, duration, priority (high / medium /
  low), category, and optional time and recurrence (daily / weekly). Tasks belong to
  a specific pet.
- **Generate a daily plan** — the scheduler ranks tasks by priority (then by shortest
  duration) and packs them into the owner's available time, starting from the top,
  until time runs out.
- **Explain the plan** — every scheduled item shows its time slot, duration, priority,
  and a short reason, so the owner understands the choices.
- **Extra scheduling helpers**:
  - *Sort by time* — order tasks chronologically by their `HH:MM` time.
  - *Filter* — view tasks by pet and/or completion status.
  - *Conflict detection* — warn when two tasks overlap in time instead of failing silently.
  - *Recurrence* — completing a daily or weekly task auto-creates the next occurrence.

## How It Works (at a glance)

The system is built from small, single-responsibility classes:

| Class | Responsibility |
|-------|----------------|
| `Owner` | Owner info, preferences, available time, list of pets |
| `Pet` | Pet profile, care notes, its own list of tasks |
| `Task` | One care action — duration, priority, recurrence, validity, priority score |
| `TimeWindow` | A start/end time span; overlap and containment checks |
| `SchedulingConstraints` | Available minutes, preferred/blocked windows, max tasks |
| `Scheduler` | The brain — ranks tasks, generates the plan, sorts, filters, detects conflicts |
| `DayPlan` | Holds the chosen `ScheduleItem`s; totals and plan explanation |
| `ScheduleItem` | One scheduled task wrapped with its time window and reason |

**Scheduling approach:** a simple *greedy* algorithm — rank by priority then duration,
fill the day sequentially from minute 0. It is fast and easy to explain. The tradeoff:
it is not a full optimizer, so it can miss subtle improvements a constraint solver would find.

## Interfaces

- **Streamlit app** (`app.py`) — interactive UI: enter owner/pet info, add tasks per
  pet, and generate per-pet daily schedules with ranking and explanations.
- **CLI demo** (`main.py`) — end-to-end walkthrough showing sorting, filtering,
  recurrence, conflict detection, and schedule generation for two example pets.
- **Tests** (`tests/test_pawpal.py`) — cover sorting order, daily recurrence rollover,
  and conflict detection.
