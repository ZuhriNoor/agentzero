"""Calendar actions: add_event, list_events."""
from . import Action
from agentzero.tools.calendar import LocalCalendarTool

# Singleton instance
_calendar = LocalCalendarTool()


def register() -> dict:
    return {
        "add_event": Action(
            name="add_event",
            description="Add an event to the local calendar (ICS).",
            run=lambda **p: _calendar.add_event(
                name=p.get("name"),
                begin=p.get("begin"),
                end=p.get("end"),
                description=p.get("description"),
                recurrence=p.get("recurrence"),
                tags=p.get("tags"),
            ),
            permission="add_event",
            category="tool",
        ),
        "list_events": Action(
            name="list_events",
            description="List events from the local calendar (ICS).",
            run=lambda **p: _calendar.list_events(
                start=p.get("start"),
                end=p.get("end"),
                tag=p.get("tag"),
            ),
            permission="list_events",
            category="tool",
        ),
    }
