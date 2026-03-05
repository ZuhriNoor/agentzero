"""Planning actions: plan_day, plan_week.
Composite actions that internally fetch events, load habits, and compose
a day/week plan via the LLM — no multi-step planner chains needed.
"""
from datetime import datetime, timedelta
from . import Action
from agentzero.tools.calendar import LocalCalendarTool
from agentzero.memory import StructuredMemory
from agentzero.llm_service import chat_completion

HABIT_MEMORY_PATH = "data/habits.json"

_calendar = LocalCalendarTool()


def _load_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get("habits", [])


def _format_events(events: list) -> str:
    if not events:
        return "No events scheduled."
    lines = []
    for e in events:
        time_str = e.get("begin", "unknown time")
        lines.append(f"- {e['name']} at {time_str}")
    return "\n".join(lines)


def _format_habits(habits: list) -> str:
    if not habits:
        return "No habits tracked."
    lines = []
    for h in habits:
        detail = h.get("name", "unnamed")
        if h.get("duration"):
            detail += f" ({h['duration']})"
        if h.get("time_of_day"):
            detail += f" at {h['time_of_day']}"
        if h.get("days_of_week"):
            detail += f" on {', '.join(h['days_of_week'])}"
        lines.append(f"- {detail}")
    return "\n".join(lines)


def plan_day(date=None, **kwargs):
    """Compose a full day plan from real calendar events + habits."""
    now = datetime.now()

    if date:
        from dateutil.parser import parse as parse_date
        target = parse_date(date)
    else:
        target = now + timedelta(days=1)  # Default to tomorrow

    start = target.strftime("%Y-%m-%d 00:00")
    end = target.strftime("%Y-%m-%d 23:59")
    day_label = target.strftime("%A, %B %d, %Y")

    # 1. Fetch real events
    events = _calendar.list_events(start=start, end=end)
    events_text = _format_events(events)

    # 2. Load habits
    habits = _load_habits()
    habits_text = _format_habits(habits)

    # 3. Ask LLM to compose the plan with real data
    messages = [
        {
            "role": "system",
            "content": (
                "You are Ein, a helpful productivity AI. "
                "Create a structured day plan using ONLY the events and habits provided below. "
                "Do NOT invent or fabricate any events. "
                "Suggest time slots for habits around the existing events. "
                "Be concise and friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Plan my day for {day_label}.\n\n"
                f"Calendar Events:\n{events_text}\n\n"
                f"Habits to include:\n{habits_text}\n\n"
                f"Current time: {now.strftime('%H:%M')}"
            ),
        },
    ]

    return chat_completion(messages=messages, stream=False, timeout=30)


def plan_week(start_date=None, **kwargs):
    """Compose a week plan from real calendar events + habits."""
    now = datetime.now()

    if start_date:
        from dateutil.parser import parse as parse_date
        target = parse_date(start_date)
    else:
        target = now + timedelta(days=1)

    end_target = target + timedelta(days=6)
    start = target.strftime("%Y-%m-%d 00:00")
    end = end_target.strftime("%Y-%m-%d 23:59")
    week_label = f"{target.strftime('%A, %B %d')} to {end_target.strftime('%A, %B %d, %Y')}"

    # 1. Fetch real events
    events = _calendar.list_events(start=start, end=end)
    events_text = _format_events(events)

    # 2. Load habits
    habits = _load_habits()
    habits_text = _format_habits(habits)

    # 3. Ask LLM to compose the plan with real data
    messages = [
        {
            "role": "system",
            "content": (
                "You are Ein, a helpful productivity AI. "
                "Create a structured week plan using ONLY the events and habits provided below. "
                "Do NOT invent or fabricate any events. "
                "Organize by day and suggest time slots for habits. "
                "Be concise and friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Plan my week: {week_label}.\n\n"
                f"Calendar Events:\n{events_text}\n\n"
                f"Habits to include:\n{habits_text}\n\n"
                f"Current time: {now.strftime('%H:%M')}"
            ),
        },
    ]

    return chat_completion(messages=messages, stream=False, timeout=30)


def register() -> dict:
    return {
        "plan_day": Action(
            name="plan_day",
            description="Create a structured day plan from calendar events and habits.",
            run=plan_day,
            permission="plan_day",
            category="skill",
        ),
        "plan_week": Action(
            name="plan_week",
            description="Create a structured week plan from calendar events and habits.",
            run=plan_week,
            permission="plan_week",
            category="skill",
        ),
    }
