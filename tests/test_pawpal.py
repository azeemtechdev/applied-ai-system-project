"""
Tests for PawPal+ scheduling system
"""

import pytest
from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


class TestTaskCompletion:
    """Test task completion status changes."""

    def test_mark_complete_changes_task_status(self):
        """Verify that calling mark_complete() sets completed to True."""
        task = Task(
            title="Morning walk",
            duration_minutes=30,
            priority="high",
        )
        
        # Initially, task should not be completed
        assert task.completed is False
        
        # After calling mark_complete(), it should be True
        task.mark_complete()
        assert task.completed is True


class TestTaskAddition:
    """Test adding tasks to pets."""

    def test_add_task_increases_pet_task_count(self):
        """Verify that adding a task to a Pet increases the task count."""
        pet = Pet(
            name="Biscuit",
            species="dog",
            breed="Golden Retriever",
            age=3,
        )
        
        # Initially, pet should have no tasks
        assert len(pet.tasks) == 0
        
        # Create and add a task
        task = Task(
            title="Morning walk",
            duration_minutes=30,
            priority="high",
        )
        pet.add_task(task)
        
        # After adding, task count should be 1
        assert len(pet.tasks) == 1
        
        # Add another task
        task2 = Task(
            title="Feeding",
            duration_minutes=10,
            priority="high",
        )
        pet.add_task(task2)
        
        # Task count should now be 2
        assert len(pet.tasks) == 2


class TestSchedulerUtilities:
    def test_sort_by_time_orders_tasks_by_hhmm_string(self):
        owner = Owner(name="Jordan")
        pet = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
        tasks = [
            Task(title="Evening walk", duration_minutes=30, priority="low", time="18:30", pet=pet),
            Task(title="Breakfast", duration_minutes=10, priority="high", time="07:15", pet=pet),
            Task(title="Lunch", duration_minutes=20, priority="medium", time="12:00", pet=pet),
        ]
        scheduler = Scheduler(owner=owner, pet=pet, tasks=tasks)

        sorted_titles = [task.title for task in scheduler.sort_by_time()]

        assert sorted_titles == ["Breakfast", "Lunch", "Evening walk"]

    def test_filter_tasks_by_pet_and_completion_status(self):
        owner = Owner(name="Jordan")
        biscuit = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
        whiskers = Pet(name="Whiskers", species="cat", breed="Tabby", age=5)
        task_one = Task(title="Morning walk", duration_minutes=30, priority="high", completed=True, pet=biscuit)
        task_two = Task(title="Feed cat", duration_minutes=10, priority="high", completed=False, pet=whiskers)
        scheduler = Scheduler(owner=owner, tasks=[task_one, task_two])

        biscuit_completed = scheduler.filter_tasks(pet_name="Biscuit", completed=True)
        pending_tasks = scheduler.filter_tasks(completed=False)

        assert biscuit_completed == [task_one]
        assert pending_tasks == [task_two]

    def test_mark_task_complete_creates_next_daily_occurrence(self):
        owner = Owner(name="Jordan")
        pet = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
        task = Task(
            title="Morning walk",
            duration_minutes=30,
            priority="high",
            recurrence="daily",
            due_date=date(2026, 7, 5),
            pet=pet,
        )
        scheduler = Scheduler(owner=owner, pet=pet, tasks=[task])

        next_task = scheduler.mark_task_complete(task)

        assert task.completed is True
        assert next_task is not None
        assert next_task.due_date == date(2026, 7, 6)
        assert next_task.completed is False

    def test_detect_conflicts_returns_warning_for_overlapping_tasks(self):
        owner = Owner(name="Jordan")
        biscuit = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
        whiskers = Pet(name="Whiskers", species="cat", breed="Tabby", age=5)
        task_one = Task(title="Morning walk", duration_minutes=30, priority="high", time="08:00", pet=biscuit)
        task_two = Task(title="Morning meds", duration_minutes=5, priority="high", time="08:00", pet=whiskers)
        scheduler = Scheduler(owner=owner, tasks=[task_one, task_two])

        warnings = scheduler.detect_conflicts()

        assert len(warnings) == 1
        assert "overlap" in warnings[0]
