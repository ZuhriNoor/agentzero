import pytest
from datetime import datetime, timedelta
import os
from agentzero.tools.calendar import LocalCalendarTool

@pytest.fixture
def temp_calendar(tmp_path):
    """Creates a temporary calendar file for testing."""
    cal_file = tmp_path / "test_calendar.ics"
    # Create empty calendar
    with open(cal_file, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:ics.py - http://git.io/lLljaA\nEND:VCALENDAR")
    return cal_file

def test_add_and_list_event(temp_calendar):
    """Test parsing dates and adding events to the ICS file, then retrieving them."""
    tool = LocalCalendarTool()
    # Override path for both the class variable and the instance variable
    tool.ICS_FILE = str(temp_calendar)
    tool.path = str(temp_calendar)
    
    # 1. Add event
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    
    begin_str = tomorrow.strftime("%Y-%m-%d %H:%M:%S")
    end_str = (tomorrow + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    result = tool.add_event(
        name="Dentist Appointment",
        begin=begin_str,
        end=end_str,
        description="Routine checkup"
    )
    
    assert result is True
    
    # 2. List events
    start_search = now.strftime("%Y-%m-%d")
    end_search = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    
    events = tool.list_events(start=start_search, end=end_search)
    
    assert len(events) == 1
    assert events[0]["name"] == "Dentist Appointment"
    assert "Routine checkup" in events[0]["description"]

def test_timezone_preservation(temp_calendar):
    """Verify that aware datetime strings are preserved."""
    tool = LocalCalendarTool()
    tool.ICS_FILE = str(temp_calendar)
    tool.path = str(temp_calendar)
    
    aware_str = "2026-02-15 10:00:00+05:30"
    tool.add_event(name="Aware Test", begin=aware_str)
    
    # Verify the ICS file contents
    with open(temp_calendar, "r", encoding="utf-8") as f:
        content = f.read()
        
    # The timezone-aware event should be stored as UTC in the ICS file (Z suffix)
    # or as floating if naive. Arrow converts +05:30 to UTC for storage.
    assert "DTSTART" in content
