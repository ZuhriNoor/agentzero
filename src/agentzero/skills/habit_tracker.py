"""
Habit Tracker Skill for AgentZero.
Manages habits in structured memory and can sync with calendar as needed.
"""
from agentzero.memory import StructuredMemory

HABIT_MEMORY_PATH = 'data/habits.json'


def add_habit(name, time_of_day=None, days_of_week=None, description=None):
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    if 'habits' not in data:
        data['habits'] = []
    habit = {
        'name': name,
        'time_of_day': time_of_day,
        'days_of_week': days_of_week,
        'description': description,
        'history': [],
    }
    data['habits'].append(habit)
    mem.save(data)
    return f"Habit '{name}' added successfully."


def list_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get('habits', [])


def mark_habit_completed(name, date=None):
    from datetime import datetime as dt
    if not date:
        date = dt.now().strftime('%Y-%m-%d')
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    for habit in data.get('habits', []):
        if habit['name'].lower() == name.lower():
            habit.setdefault('history', []).append(date)
            mem.save(data)
            return f"Habit '{name}' marked as completed for {date}."
    return f"Habit '{name}' not found."
