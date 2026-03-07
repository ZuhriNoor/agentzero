"""Planning actions: plan_day, plan_week.
Composite actions that internally fetch events, load habits, and compose
a day/week plan via the LLM — no multi-step planner chains needed.
"""
from datetime import datetime, timedelta
from dateutil import tz
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

def _load_tasks():
    mem = StructuredMemory("data/tasks.json")
    data = mem.load()
    return [t for t in data.get("tasks", []) if not t.get("completed")]


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

def _format_tasks(tasks: list) -> str:
    if not tasks:
        return "No pending tasks."
    lines = []
    for t in tasks:
        line = f"- {t['task']}"
        if t.get('deadline'):
            line += f" (Due: {t['deadline']})"
        lines.append(line)
    return "\n".join(lines)


async def plan_day(date=None, **kwargs):
    """Compose a full day plan from real calendar events + habits."""
    now = datetime.now(tz.tzlocal())

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

    # 3. Load tasks
    tasks = _load_tasks()
    tasks_text = _format_tasks(tasks)

    # 4. Ask LLM to compose the plan with real data
    messages = [
        {
            "role": "system",
            "content": (
                "You are Ein, a realistic and helpful daily scheduler. "
                "Create a structured day plan using ONLY the events, habits, and tasks provided below. "
                "IMPORTANT RULES: "
                "1. Prioritize scheduling Calendar Events at their exact fixed times. "
                "2. Fit Habits into their designated time of day. "
                "3. Assign pending Tasks to empty blocks in the schedule. "
                "4. Do NOT invent or fabricate any events, habits, or tasks. If there is free time, explicitly label it as 'Free Time'. "
                "Be concise and friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Plan my day for {day_label}.\n\n"
                f"Calendar Events:\n{events_text}\n\n"
                f"Habits to include:\n{habits_text}\n\n"
                f"Pending Tasks:\n{tasks_text}\n\n"
                f"Current time: {now.strftime('%H:%M')}"
            ),
        },
    ]

    return await chat_completion(messages=messages, stream=False, timeout=30)


async def plan_week(start_date=None, **kwargs):
    """Compose a week plan from real calendar events + habits."""
    now = datetime.now(tz.tzlocal())

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

    # 3. Load tasks
    tasks = _load_tasks()
    tasks_text = _format_tasks(tasks)

    # 4. Ask LLM to compose the plan with real data
    messages = [
        {
            "role": "system",
            "content": (
                "You are Ein, a realistic and helpful weekly scheduler. "
                "Create a structured week plan using ONLY the events, habits, and tasks provided below. "
                "IMPORTANT RULES: "
                "1. Prioritize scheduling Calendar Events at their exact fixed times. "
                "2. Fit Habits into their designated time of day. "
                "3. Spread pending Tasks across the week into empty blocks. "
                "4. Do NOT invent or fabricate any events, habits, or tasks. If there is open space, leave it as 'Free Time'. "
                "Organize by day. Be concise and friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Plan my week: {week_label}.\n\n"
                f"Calendar Events:\n{events_text}\n\n"
                f"Habits to include:\n{habits_text}\n\n"
                f"Pending Tasks:\n{tasks_text}\n\n"
                f"Current time: {now.strftime('%H:%M')}"
            ),
        },
    ]

    return await chat_completion(messages=messages, stream=False, timeout=30)


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
