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
        
        # Parse 'begin' as Local Time if it is a naive string
        # We assume the user input (from planner) is in the system's local time
        import arrow
        from dateutil import tz
        
        try:
            # arrow.get(..., tzinfo=...) works well
            # If begin is naive string "2026-02-15 10:00", treat as Local
            begin_arrow = arrow.get(begin, tzinfo=tz.tzlocal())
            event.begin = begin_arrow.datetime
        except:
            # Fallback
            event.begin = begin
            
        if end:
            try:
                end_arrow = arrow.get(end, tzinfo=tz.tzlocal())
                event.end = end_arrow.datetime
            except:
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
            
        # Helper to convert to local system time for display
        from dateutil import tz
        def to_local(arrow_time):
            # ics uses arrow or datetime. Convert to datetime then astimezone
            dt = arrow_time.datetime if hasattr(arrow_time, 'datetime') else arrow_time
            return dt.astimezone(tz.tzlocal()).isoformat()

        return [{
            'name': e.name,
            'begin': to_local(e.begin),
            'end': to_local(e.end) if e.end else None,
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
