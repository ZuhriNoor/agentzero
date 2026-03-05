"""
Skill interface and loader for AgentZero. Skills are modular, API-agnostic, and loaded locally.
"""
from typing import Any, Dict, Callable, Optional

class Skill:
    def __init__(self, name: str, description: str, run: Callable, permission: Optional[str] = None):
        self.name = name
        self.description = description
        self.run = run
        self.permission = permission or name  # Defaults to skill name

def load_skills() -> Dict[str, Skill]:
    from .add_task import AddTaskSkill
    from .habit_tracker import add_habit, list_habits, mark_habit_completed

    return {
        "add_task": AddTaskSkill(),
        "add_habit": Skill(
            name="add_habit",
            description="Add a new habit to track (name, time_of_day, days_of_week).",
            run=add_habit,
            permission="add_habit",
        ),
        "list_habits": Skill(
            name="list_habits",
            description="List all tracked habits.",
            run=list_habits,
            permission="list_habits",
        ),
        "track_habit": Skill(
            name="track_habit",
            description="Mark a habit as completed for a given date.",
            run=mark_habit_completed,
            permission="track_habit",
        ),
    }
