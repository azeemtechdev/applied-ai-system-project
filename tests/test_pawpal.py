"""
Tests for PawPal+ scheduling system
"""

import pytest
from pawpal_system import Pet, Task


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
