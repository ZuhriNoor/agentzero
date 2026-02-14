"""
Local Calendar Tool for AgentZero.
Manages events and schedules using a local ICS file.
"""
import os
from datetime import datetime, timedelta
from ics import Calendar, Event

CALENDAR_PATH = 'data/calendar.ics'

class LocalCalendarTool:
    def __init__(self, path=CALENDAR_PATH):
        self.path = path
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write('BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//AgentZero//EN\nEND:VCALENDAR\n')

    def _load_calendar(self):
        try:
            with open(self.path, 'r') as f:
                content = f.read()
                try:
                    return Calendar(content)
                except Exception as e:
                    # Check for multiple calendars error
                    if 'multiple calendars' in str(e).lower():
                        # Reset file to a single empty calendar with PRODID
                        empty_ical = 'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//AgentZero//EN\nEND:VCALENDAR\n'
                        with open(self.path, 'w') as fw:
                            fw.write(empty_ical)
                        return Calendar(empty_ical)
                    raise
        except FileNotFoundError:
            empty_ical = 'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//AgentZero//EN\nEND:VCALENDAR\n'
            with open(self.path, 'w') as f:
                f.write(empty_ical)
            return Calendar(empty_ical)

    def _save_calendar(self, cal):
        with open(self.path, 'w') as f:
            f.writelines(cal.serialize_iter())

    def add_event(self, name, begin, end=None, description=None, recurrence=None, tags=None):
        cal = self._load_calendar()
        event = Event()
        event.name = name
        event.begin = begin
        if end:
            event.end = end
        if description:
            event.description = description
        if tags:
            event.categories = tags
        if recurrence:
            event.extra.append(('RRULE', recurrence))
        cal.events.add(event)
        self._save_calendar(cal)
        return True

    def list_events(self, start=None, end=None, tag=None):
        from dateutil.parser import parse as parse_date
        import arrow
        cal = self._load_calendar()
        events = list(cal.events)
        start_arrow = None
        end_arrow = None
        if start:
            try:
                start_arrow = arrow.get(parse_date(start))
            except Exception:
                start_arrow = None
        if end:
            try:
                end_arrow = arrow.get(parse_date(end))
            except Exception:
                end_arrow = None
        # Filter by start/end range
        if start_arrow:
            events = [e for e in events if e.begin >= start_arrow]
        if end_arrow:
            events = [e for e in events if e.begin <= end_arrow]
        if tag:
            events = [e for e in events if tag in (e.categories or set())]
        return [{
            'name': e.name,
            'begin': str(e.begin),
            'end': str(e.end) if e.end else None,
            'description': e.description,
            'tags': list(e.categories) if e.categories else [],
        } for e in events]

    def remove_event(self, name, begin):
        cal = self._load_calendar()
        to_remove = [e for e in cal.events if e.name == name and str(e.begin) == str(begin)]
        for e in to_remove:
            cal.events.remove(e)
        self._save_calendar(cal)
        return len(to_remove) > 0
