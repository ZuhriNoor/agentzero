"""
Example skill: Add a task to the local planner (structured memory) and associate with local calendar.
"""
from . import Skill
from memory import StructuredMemory
from tools.calendar import LocalCalendarTool
from datetime import datetime

def add_task_to_planner(task: str, due: str = None, calendar_event: dict = None):
    mem = StructuredMemory('data/tasks.json')
    data = mem.load()
    if 'tasks' not in data:
        data['tasks'] = []
    task_entry = {"task": task, "due": due}
    # Optionally create a calendar event
    if calendar_event:
        cal = LocalCalendarTool()
        event_name = calendar_event.get('name', task)
        event_begin = calendar_event.get('begin', due)
        event_end = calendar_event.get('end')
        event_desc = calendar_event.get('description')
        recurrence = calendar_event.get('recurrence')
        tags = calendar_event.get('tags', ['task'])
        cal.add_event(
            name=event_name,
            begin=event_begin,
            end=event_end,
            description=event_desc,
            recurrence=recurrence,
            tags=tags
        )
        task_entry['calendar_event'] = event_name
    data['tasks'].append(task_entry)
    mem.save(data)
    return True

class AddTaskSkill(Skill):
    def __init__(self):
        super().__init__(
            name="add_task",
            description="Add a task to the local planner and calendar.",
            run=add_task_to_planner
        )
