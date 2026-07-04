#!/usr/bin/env python3
"""
PawPal+ Demo Script

This script demonstrates the scheduling system by:
1. Creating an owner and pets
2. Adding care tasks to those pets
3. Generating and displaying a daily schedule
"""

from datetime import date
from pawpal_system import (
    Owner,
    Pet,
    Task,
    TimeWindow,
    Scheduler,
    SchedulingConstraints,
)


def main():
    print("=" * 60)
    print("PawPal+ Daily Schedule Generator")
    print("=" * 60)
    print()

    # Create an owner
    owner = Owner(
        name="Jordan",
        preferences="Morning person; prefer walks before 10 AM",
        available_time_minutes=480,  # 8 hours
        notes="Busy schedule, needs efficient planning",
    )
    print(f"Owner: {owner.name}")
    print(f"  Preferences: {owner.preferences}")
    print(f"  Available time: {owner.available_time_minutes} minutes")
    print()

    # Create pets
    dog = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)
    cat = Pet(name="Whiskers", species="cat", breed="Tabby", age=5)

    owner.add_pet(dog)
    owner.add_pet(cat)

    print(f"Pets managed by {owner.name}:")
    for pet in owner.pets:
        print(f"  - {pet.get_summary()}")
    print()

    # Create tasks for Biscuit (dog)
    morning_walk = Task(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        category="exercise",
        recurrence="daily",
        pet=dog,
    )
    dog.add_task(morning_walk)

    feeding_biscuit = Task(
        title="Feed Biscuit",
        duration_minutes=10,
        priority="high",
        category="nutrition",
        recurrence="daily",
        pet=dog,
    )
    dog.add_task(feeding_biscuit)

    playtime = Task(
        title="Playtime with Biscuit",
        duration_minutes=20,
        priority="medium",
        category="enrichment",
        recurrence="daily",
        pet=dog,
    )
    dog.add_task(playtime)

    # Create tasks for Whiskers (cat)
    feeding_whiskers = Task(
        title="Feed Whiskers",
        duration_minutes=5,
        priority="high",
        category="nutrition",
        recurrence="daily",
        pet=cat,
    )
    cat.add_task(feeding_whiskers)

    grooming = Task(
        title="Brush Whiskers",
        duration_minutes=15,
        priority="medium",
        category="grooming",
        recurrence="daily",
        pet=cat,
    )
    cat.add_task(grooming)

    print(f"Tasks for {dog.name}:")
    for task in dog.tasks:
        print(f"  - {task.title} ({task.duration_minutes}m, {task.priority} priority)")
    print()

    print(f"Tasks for {cat.name}:")
    for task in cat.tasks:
        print(f"  - {task.title} ({task.duration_minutes}m, {task.priority} priority)")
    print()

    # Create scheduling constraints
    constraints = SchedulingConstraints(
        available_minutes=480,  # 8 hours
        preferred_windows=[],
        blocked_windows=[],
        max_tasks=10,
    )

    # Schedule for Biscuit
    print("=" * 60)
    print(f"Generating schedule for {dog.name}...")
    print("=" * 60)

    scheduler_dog = Scheduler(
        owner=owner,
        pet=dog,
        tasks=dog.tasks,
        constraints=constraints,
    )

    plan_dog = scheduler_dog.generate_schedule()
    print()
    print(plan_dog.explain_plan())
    print()

    # Schedule for Whiskers
    print("=" * 60)
    print(f"Generating schedule for {cat.name}...")
    print("=" * 60)

    scheduler_cat = Scheduler(
        owner=owner,
        pet=cat,
        tasks=cat.tasks,
        constraints=constraints,
    )

    plan_cat = scheduler_cat.generate_schedule()
    print()
    print(plan_cat.explain_plan())
    print()

    # Summary
    print("=" * 60)
    print("Daily Schedule Summary")
    print("=" * 60)
    print(f"Total tasks scheduled for {dog.name}: {len(plan_dog.scheduled_items)}")
    print(f"Total tasks scheduled for {cat.name}: {len(plan_cat.scheduled_items)}")
    print(f"Owner's available time: {owner.available_time_minutes} minutes")
    print()


if __name__ == "__main__":
    main()
