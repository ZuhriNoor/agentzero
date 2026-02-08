"""
Habit Tracker Skill for AgentZero.
Manages habits in structured memory and can sync with calendar as needed.
"""
from . import Skill
from memory import StructuredMemory
from tools.calendar import LocalCalendarTool
from datetime import datetime

HABIT_MEMORY_PATH = 'data/habits.json'

# Add a new habit to structured memory
def add_habit(name, time_of_day, days_of_week, description=None):
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    if 'habits' not in data:
        data['habits'] = []
    habit = {
        'name': name,
        'time_of_day': time_of_day,  # e.g., '07:00'
        'days_of_week': days_of_week,  # e.g., ['MO', 'WE', 'FR']
        'description': description,
        'history': []  # Track completions
    }
    data['habits'].append(habit)
    mem.save(data)
    return True

# List all habits from structured memory
def list_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get('habits', [])

# Mark a habit as completed for a given date
def mark_habit_completed(name, date):
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    for habit in data.get('habits', []):
        if habit['name'] == name:
            habit.setdefault('history', []).append(date)
            mem.save(data)
            return {"habit": name, "date": date, "status": "completed"}
    return {"habit": name, "date": date, "status": "not found"}

class HabitTrackerSkill(Skill):
    def __init__(self):
        super().__init__(
            name="habit_tracker",
            description="Manage and track habits in structured memory.",
            run=None  # Use add_habit, list_habits, mark_habit_completed directly
        )
