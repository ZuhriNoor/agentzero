"""
Example skill: Add a task to the local planner (structured memory).
"""
from . import Skill
from memory import StructuredMemory

def add_task_to_planner(task: str, due: str = None):
    mem = StructuredMemory('data/tasks.json')
    data = mem.load()
    if 'tasks' not in data:
        data['tasks'] = []
    data['tasks'].append({"task": task, "due": due})
    mem.save(data)
    return True

class AddTaskSkill(Skill):
    def __init__(self):
        super().__init__(
            name="add_task",
            description="Add a task to the local planner (structured memory).",
            run=add_task_to_planner
        )
