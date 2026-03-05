"""Habit actions: add_habit, list_habits, track_habit."""
from . import Action
from agentzero.memory import StructuredMemory

HABIT_MEMORY_PATH = "data/habits.json"


def add_habit(name, time_of_day=None, days_of_week=None, description=None, **kwargs):
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    if "habits" not in data:
        data["habits"] = []
    habit = {
        "name": name,
        "time_of_day": time_of_day,
        "days_of_week": days_of_week,
        "description": description,
        "history": [],
        **kwargs,  # Store any extra params (duration, frequency, etc.)
    }
    data["habits"].append(habit)
    mem.save(data)
    return f"Habit '{name}' added successfully."


def list_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get("habits", [])


def mark_habit_completed(name, date=None):
    from datetime import datetime as dt

    if not date:
        date = dt.now().strftime("%Y-%m-%d")
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    for habit in data.get("habits", []):
        if habit["name"].lower() == name.lower():
            habit.setdefault("history", []).append(date)
            mem.save(data)
            return f"Habit '{name}' marked as completed for {date}."
    return f"Habit '{name}' not found."


def register() -> dict:
    return {
        "add_habit": Action(
            name="add_habit",
            description="Add a new habit to track (name, time_of_day, days_of_week).",
            run=add_habit,
            permission="add_habit",
            category="skill",
        ),
        "list_habits": Action(
            name="list_habits",
            description="List all tracked habits.",
            run=list_habits,
            permission="list_habits",
            category="skill",
        ),
        "track_habit": Action(
            name="track_habit",
            description="Mark a habit as completed for a given date.",
            run=mark_habit_completed,
            permission="track_habit",
            category="skill",
        ),
    }
