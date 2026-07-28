from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import List


@dataclass
class TimeWindow:
	start_minute: int = 0
	end_minute: int = 0

	def duration_minutes(self) -> int:
		"""Calculate the duration in minutes between start and end."""
		return max(0, self.end_minute - self.start_minute)

	def contains(self, minute: int) -> bool:
		"""Check if a given minute falls within this time window."""
		return self.start_minute <= minute <= self.end_minute

	def overlaps(self, other: "TimeWindow") -> bool:
		"""Check if this time window overlaps with another."""
		if other is None:
			return False
		return not (self.end_minute <= other.start_minute or self.start_minute >= other.end_minute)


@dataclass
class SchedulingConstraints:
	available_minutes: int = 0
	preferred_windows: List[TimeWindow] = field(default_factory=list)
	blocked_windows: List[TimeWindow] = field(default_factory=list)
	max_tasks: int = 0


@dataclass
class Owner:
	name: str = ""
	preferences: str = ""
	available_time_minutes: int = 0
	notes: str = ""
	pets: List["Pet"] = field(default_factory=list)

	def update_preferences(self, preferences: str) -> None:
		"""Update the owner's care preferences."""
		self.preferences = preferences

	def set_available_time(self, minutes: int) -> None:
		"""Set the owner's available time in minutes."""
		self.available_time_minutes = minutes

	def add_pet(self, pet: "Pet") -> None:
		"""Add a pet to the owner's care and set ownership relationship."""
		if pet not in self.pets:
			self.pets.append(pet)
			pet.owner = self


@dataclass
class Pet:
	name: str = ""
	species: str = ""
	breed: str = ""
	age: int = 0
	care_notes: str = ""
	owner: Owner | None = None
	tasks: List["Task"] = field(default_factory=list)

	def update_profile(self, name: str, species: str, breed: str, age: int) -> None:
		"""Update the pet's profile information."""
		self.name = name
		self.species = species
		self.breed = breed
		self.age = age

	def add_task(self, task: "Task") -> None:
		"""Add a care task to this pet and set ownership relationship."""
		if task not in self.tasks:
			self.tasks.append(task)
			task.pet = self

	def get_summary(self) -> str:
		"""Return a formatted summary of the pet's basic information."""
		return f"{self.name} ({self.species}, {self.breed}), age {self.age}"


@dataclass
class Task:
	title: str = ""
	duration_minutes: int = 0
	priority: str = ""
	category: str = ""
	recurrence: str = ""
	time: str = ""
	due_date: date | None = None
	preferred_window: TimeWindow | None = None
	pet: "Pet" | None = None
	completed: bool = False

	def is_valid(self) -> bool:
		"""Check if task has a title and positive duration."""
		return bool(self.title and self.duration_minutes > 0)

	def get_priority_score(self) -> int:
		"""Return a numeric score for the task's priority level."""
		priority_map = {"high": 3, "medium": 2, "low": 1}
		return priority_map.get(self.priority, 0)

	def mark_complete(self) -> None:
		"""Mark the task as completed."""
		self.completed = True

	def get_next_occurrence(self) -> "Task" | None:
		"""Create the next recurring instance for daily or weekly tasks."""
		if self.recurrence not in {"daily", "weekly"}:
			return None

		days_ahead = 1 if self.recurrence == "daily" else 7
		next_due_date = (self.due_date or date.today()) + timedelta(days=days_ahead)
		return replace(self, completed=False, due_date=next_due_date)

	def can_fit_into(self, time_remaining: int) -> bool:
		"""Check if task duration fits within remaining available time."""
		return self.duration_minutes <= time_remaining

	@classmethod
	def from_dict(cls, data: dict, pet: "Pet" | None = None) -> "Task":
		"""Build a Task from a validated dict (used by the AI agent layer)."""
		return cls(
			title=data.get("title", ""),
			duration_minutes=int(data.get("duration_minutes", 0)),
			priority=data.get("priority", "medium"),
			category=data.get("category", "care"),
			pet=pet,
		)


@dataclass
class ScheduleItem:
	task: Task | None = None
	window: TimeWindow | None = None
	reason: str = ""

	def format_entry(self) -> str:
		"""Format the schedule item as a human-readable string with time and reasoning."""
		if not self.task or not self.window:
			return "Invalid schedule item"
		start_h, start_m = divmod(self.window.start_minute, 60)
		end_h, end_m = divmod(self.window.end_minute, 60)
		time_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
		return f"{time_str} | {self.task.title} ({self.task.duration_minutes}m) [priority: {self.task.priority}]\n  Reason: {self.reason}"

	def conflicts_with(self, other: "ScheduleItem") -> bool:
		"""Check if this schedule item conflicts (overlaps) with another."""
		if not self.window or not other.window:
			return False
		return self.window.overlaps(other.window)


@dataclass
class DayPlan:
	date: date | None = None
	available_minutes: int = 0
	owner: Owner | None = None
	pet: Pet | None = None
	scheduled_items: List[ScheduleItem] = field(default_factory=list)

	def add_item(self, item: ScheduleItem) -> None:
		"""Add a scheduled item to the daily plan."""
		self.scheduled_items.append(item)

	def get_total_scheduled_minutes(self) -> int:
		"""Calculate the total minutes scheduled across all items in the plan."""
		total = 0
		for item in self.scheduled_items:
			if item.window:
				total += item.window.duration_minutes()
		return total

	def get_remaining_minutes(self) -> int:
		"""Calculate the remaining available time after all scheduled items."""
		return self.available_minutes - self.get_total_scheduled_minutes()

	def explain_plan(self) -> str:
		"""Generate a formatted explanation of the daily plan with all scheduled tasks and remaining time."""
		if self.pet:
			plan_str = f"Daily plan for {self.pet.name}:\n"
		else:
			plan_str = f"Daily plan for {self.date}:\n"
		for item in self.scheduled_items:
			plan_str += item.format_entry() + "\n"
		plan_str += f"\nTotal scheduled: {self.get_total_scheduled_minutes()} minutes\n"
		plan_str += f"Remaining time: {self.get_remaining_minutes()} minutes"
		return plan_str


@dataclass
class Scheduler:
	owner: Owner | None = None
	pet: Pet | None = None
	tasks: List[Task] = field(default_factory=list)
	constraints: SchedulingConstraints | None = None

	def _time_to_minutes(self, time_value: str) -> int:
		"""Convert an HH:MM string into minutes since midnight."""
		if not time_value:
			return 24 * 60
		hours, minutes = (int(part) for part in time_value.split(":"))
		return hours * 60 + minutes

	def sort_by_time(self, tasks: List[Task] | None = None) -> List[Task]:
		"""Sort tasks by their HH:MM time string.

		Tasks without a time are placed last, and ties are broken by
		priority score and then by shorter duration.
		"""
		tasks_to_sort = tasks if tasks is not None else self.tasks
		return sorted(
			tasks_to_sort,
			key=lambda task: (
				self._time_to_minutes(task.time),
				-task.get_priority_score(),
				task.duration_minutes,
			),
		)

	def filter_tasks(
		self,
		pet_name: str | None = None,
		completed: bool | None = None,
		tasks: List[Task] | None = None,
	) -> List[Task]:
		"""Return tasks that match the requested pet name and completion status.

		This helper supports simple UI filtering and terminal demos without
		requiring callers to duplicate selection logic.
		"""
		tasks_to_filter = tasks if tasks is not None else self.tasks
		filtered_tasks: List[Task] = []
		for task in tasks_to_filter:
			if pet_name and (not task.pet or task.pet.name != pet_name):
				continue
			if completed is not None and task.completed != completed:
				continue
			filtered_tasks.append(task)
		return filtered_tasks

	def mark_task_complete(self, task: Task) -> Task | None:
		"""Mark a task complete and clone the next recurring instance when needed.

		Daily tasks roll forward by one day and weekly tasks roll forward by
		seven days. Non-recurring tasks return None.
		"""
		task.mark_complete()
		next_task = task.get_next_occurrence()
		if next_task and task.pet:
			task.pet.add_task(next_task)
			if next_task not in self.tasks:
				self.tasks.append(next_task)
		return next_task

	def detect_conflicts(self, tasks: List[Task] | None = None) -> List[str]:
		"""Detect overlapping task times and return human-readable warnings.

		The check is intentionally lightweight: it flags tasks that overlap on
		the same day instead of attempting full rescheduling or optimization.
		"""
		tasks_to_check = [task for task in (tasks if tasks is not None else self.tasks) if task.time]
		warnings: List[str] = []

		for index, left_task in enumerate(tasks_to_check):
			left_start = self._time_to_minutes(left_task.time)
			left_end = left_start + left_task.duration_minutes

			for right_task in tasks_to_check[index + 1 :]:
				if left_task.due_date and right_task.due_date and left_task.due_date != right_task.due_date:
					continue

				right_start = self._time_to_minutes(right_task.time)
				right_end = right_start + right_task.duration_minutes

				if left_end <= right_start or right_end <= left_start:
					continue

				pet_scope = "the same pet"
				if left_task.pet and right_task.pet and left_task.pet != right_task.pet:
					pet_scope = f"different pets ({left_task.pet.name} and {right_task.pet.name})"
				elif left_task.pet and right_task.pet:
					pet_scope = f"{left_task.pet.name}"

				warnings.append(
					f"Conflict: '{left_task.title}' at {left_task.time} and '{right_task.title}' at {right_task.time} overlap for {pet_scope}."
				)

		return warnings

	def rank_tasks(self) -> List[Task]:
		"""Sort tasks by priority (highest first), then by duration (shortest first)."""
		valid_tasks = [t for t in self.tasks if t.is_valid()]
		return sorted(
			valid_tasks,
			key=lambda t: (-t.get_priority_score(), t.duration_minutes)
		)

	def check_constraints(self) -> bool:
		"""Check if constraints are satisfied (basic check: total duration fits)."""
		if not self.constraints:
			return True
		total_minutes = sum(t.duration_minutes for t in self.tasks if t.is_valid())
		return total_minutes <= self.constraints.available_minutes

	def resolve_conflicts(self) -> None:
		"""Remove or reschedule conflicting items (currently removes conflicts)."""
		for i, item1 in enumerate(self.tasks):
			for item2 in self.tasks[i + 1:]:
				if (
					item1.preferred_window
					and item2.preferred_window
					and item1.preferred_window.overlaps(item2.preferred_window)
				):
					if item2.get_priority_score() < item1.get_priority_score():
						self.tasks.remove(item2)

	def generate_schedule(self) -> DayPlan:
		"""Generate a day plan by ranking and fitting tasks into time windows."""
		if not self.owner or not self.pet or not self.constraints:
			return DayPlan(owner=self.owner, pet=self.pet)

		plan = DayPlan(
			date=date.today(),
			available_minutes=self.constraints.available_minutes,
			owner=self.owner,
			pet=self.pet,
		)

		# Rank tasks and filter to fit in available time
		ranked_tasks = self.rank_tasks()
		current_minute = 0

		for task in ranked_tasks:
			if current_minute + task.duration_minutes > self.constraints.available_minutes:
				break

			# Create a schedule window
			window = TimeWindow(
				start_minute=current_minute,
				end_minute=current_minute + task.duration_minutes,
			)

			reason = f"Priority {task.priority}; allocated slot {current_minute}-{current_minute + task.duration_minutes} minutes"

			schedule_item = ScheduleItem(
				task=task,
				window=window,
				reason=reason,
			)

			plan.add_item(schedule_item)
			current_minute += task.duration_minutes

		return plan
