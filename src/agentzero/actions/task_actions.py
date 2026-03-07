"""Task actions: add_task, list_tasks, edit_task, complete_task."""
from . import Action
from agentzero.memory import StructuredMemory

TASKS_FILE = "data/tasks.json"

def _load_tasks():
    mem = StructuredMemory(TASKS_FILE)
    data = mem.load()
    if "tasks" not in data:
        data["tasks"] = []
    return data, mem

def add_task(task: str, deadline: str = None):
    data, mem = _load_tasks()
    task_entry = {"task": task, "deadline": deadline, "completed": False}
    data["tasks"].append(task_entry)
    mem.save(data)
    
    msg = f"Task '{task}' added successfully."
    if deadline:
        msg += f" Deadline: {deadline}."
    return msg

def list_tasks():
    data, _ = _load_tasks()
    pending = [t for t in data["tasks"] if not t.get("completed")]
    if not pending:
        return "No pending tasks."
    
    lines = []
    for t in pending:
        line = f"- {t['task']}"
        if t.get('deadline'):
            line += f" (Due: {t['deadline']})"
        lines.append(line)
    return "\n".join(lines)

def edit_task(old_name: str, new_name: str = None, new_deadline: str = None):
    data, mem = _load_tasks()
    for t in data["tasks"]:
        if t["task"].lower() == old_name.lower() and not t.get("completed"):
            if new_name:
                t["task"] = new_name
            if new_deadline:
                t["deadline"] = new_deadline
            mem.save(data)
            return f"Task updated successfully."
    return f"Error: Pending task '{old_name}' not found."

def complete_task(task_name: str):
    data, mem = _load_tasks()
    for t in data["tasks"]:
        if t["task"].lower() == task_name.lower() and not t.get("completed"):
            t["completed"] = True
            mem.save(data)
            return f"Task '{task_name}' marked as completed."
    return f"Error: Pending task '{task_name}' not found."

def register() -> dict:
    return {
        "add_task": Action(
            name="add_task",
            description="Add a task with an optional deadline.",
            run=add_task,
            permission="add_task",
            category="skill",
        ),
        "list_tasks": Action(
            name="list_tasks",
            description="List all pending tasks.",
            run=list_tasks,
            permission="list_tasks",
            category="skill",
        ),
        "edit_task": Action(
            name="edit_task",
            description="Edit a task's name or deadline.",
            run=edit_task,
            permission="edit_task",
            category="skill",
        ),
        "complete_task": Action(
            name="complete_task",
            description="Mark a task as completed.",
            run=complete_task,
            permission="complete_task",
            category="skill",
        ),
    }
