"""
Tool interface and loader for AgentZero. All tools are local-only and permission-gated.
"""
from typing import Any, Dict, Callable

class Tool:
    def __init__(self, name: str, description: str, run: Callable, permission: str):
        self.name = name
        self.description = description
        self.run = run
        self.permission = permission  # Permission key for policy enforcement

def load_tools() -> Dict[str, Tool]:
    # Dynamically load tool modules from tools/ directory
    # For now, return a static example
    from .local_filesystem import LocalFileSystemTool
    from .calendar import LocalCalendarTool
    def add_event_tool(**params):
        cal = LocalCalendarTool()
        return cal.add_event(
            name=params.get('name'),
            begin=params.get('begin'),
            end=params.get('end'),
            description=params.get('description'),
            recurrence=params.get('recurrence'),
            tags=params.get('tags')
        )

    def list_events_tool(**params):
        cal = LocalCalendarTool()
        # Optionally filter by start/end/tag
        return cal.list_events(
            start=params.get('start'),
            end=params.get('end'),
            tag=params.get('tag')
        )
    from .memory_tool import LocalMemoryTool
    
    def remember_fact_tool(**params):
        mem_tool = LocalMemoryTool()
        return mem_tool.remember_fact(fact=params.get('fact'))

    return {
        "filesystem": LocalFileSystemTool(),
        "add_event": Tool(
            name="add_event",
            description="Add an event to the local calendar (ICS).",
            run=add_event_tool,
            permission="add_event"
        ),
        "list_events": Tool(
            name="list_events",
            description="List events from the local calendar (ICS).",
            run=list_events_tool,
            permission="list_events"
        ),
        "remember_fact": Tool(
            name="remember_fact",
            description="Save a significant fact about the user.",
            run=remember_fact_tool,
            permission="remember_fact"
        ),
        # ...add more tools...
    }
