"""
Minimal test suite for PawPal+ scheduler behaviors.

Includes tests for sorting correctness, recurrence rollover, and conflict detection.
"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def test_sorting_correctness_orders_tasks_chronologically():
    owner = Owner(name="Jordan")
    pet = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)

    tasks = [
        Task(title="Evening walk", duration_minutes=30, priority="low", time="18:30", pet=pet),
        Task(title="Breakfast", duration_minutes=10, priority="high", time="07:15", pet=pet),
        Task(title="Lunch", duration_minutes=20, priority="medium", time="12:00", pet=pet),
    ]

    scheduler = Scheduler(owner=owner, pet=pet, tasks=tasks)

    sorted_titles = [t.title for t in scheduler.sort_by_time()]

    assert sorted_titles == ["Breakfast", "Lunch", "Evening walk"]


def test_recurrence_logic_creates_next_daily_task():
    owner = Owner(name="Jordan")
    pet = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)

    original_due = date(2026, 7, 5)
    task = Task(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        recurrence="daily",
        due_date=original_due,
        pet=pet,
    )

    scheduler = Scheduler(owner=owner, pet=pet, tasks=[task])

    next_task = scheduler.mark_task_complete(task)

    assert task.completed is True
    assert next_task is not None
    assert next_task.due_date == date(2026, 7, 6)
    assert next_task.completed is False


def test_conflict_detection_flags_duplicate_times():
    owner = Owner(name="Jordan")
    biscuit = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
    whiskers = Pet(name="Whiskers", species="cat", breed="Tabby", age=5)

    task_one = Task(title="Morning walk", duration_minutes=30, priority="high", time="08:00", pet=biscuit)
    task_two = Task(title="Morning meds", duration_minutes=5, priority="high", time="08:00", pet=whiskers)

    scheduler = Scheduler(owner=owner, tasks=[task_one, task_two])

    warnings = scheduler.detect_conflicts()

    assert len(warnings) >= 1
    assert any("overlap" in w or "Conflict" in w for w in warnings)
