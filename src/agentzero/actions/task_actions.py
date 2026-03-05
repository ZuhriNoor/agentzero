"""Task actions: add_task."""
from . import Action
from agentzero.memory import StructuredMemory
from agentzero.tools.calendar import LocalCalendarTool


def add_task_to_planner(task: str, due: str = None, calendar_event: dict = None):
    mem = StructuredMemory("data/tasks.json")
    data = mem.load()
    if "tasks" not in data:
        data["tasks"] = []
    task_entry = {"task": task, "due": due}

    if calendar_event:
        cal = LocalCalendarTool()
        cal.add_event(
            name=calendar_event.get("name", task),
            begin=calendar_event.get("begin", due),
            end=calendar_event.get("end"),
            description=calendar_event.get("description"),
            recurrence=calendar_event.get("recurrence"),
            tags=calendar_event.get("tags", ["task"]),
        )
        task_entry["calendar_event"] = calendar_event.get("name", task)

    data["tasks"].append(task_entry)
    mem.save(data)
    return f"Task '{task}' added successfully."


def register() -> dict:
    return {
        "add_task": Action(
            name="add_task",
            description="Add a task to the local planner and optionally link to calendar.",
            run=add_task_to_planner,
            permission="add_task",
            category="skill",
        ),
    }
