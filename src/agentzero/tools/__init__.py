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
    from .local_filesystem import LocalFileSystemTool
    from .calendar import LocalCalendarTool
    from .memory_tool import LocalMemoryTool

    # Singleton instances — reused across all calls
    calendar = LocalCalendarTool()
    memory = LocalMemoryTool()

    return {
        "filesystem": LocalFileSystemTool(),
        "add_event": Tool(
            name="add_event",
            description="Add an event to the local calendar (ICS).",
            run=lambda **params: calendar.add_event(
                name=params.get('name'),
                begin=params.get('begin'),
                end=params.get('end'),
                description=params.get('description'),
                recurrence=params.get('recurrence'),
                tags=params.get('tags'),
            ),
            permission="add_event",
        ),
        "list_events": Tool(
            name="list_events",
            description="List events from the local calendar (ICS).",
            run=lambda **params: calendar.list_events(
                start=params.get('start'),
                end=params.get('end'),
                tag=params.get('tag'),
            ),
            permission="list_events",
        ),
        "remember_fact": Tool(
            name="remember_fact",
            description="Save a significant fact about the user to long-term memory.",
            run=lambda **params: memory.remember_fact(fact=params.get('fact')),
            permission="remember_fact",
        ),
    }
