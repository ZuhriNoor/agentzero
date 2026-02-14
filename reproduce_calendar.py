
import os
import shutil
from datetime import datetime, timedelta
from tools.calendar import LocalCalendarTool

# Use a temp calendar file
TEMP_CAL = 'data/temp_calendar.ics'
if os.path.exists(TEMP_CAL):
    os.remove(TEMP_CAL)

def test_calendar_logic():
    print("Testing Calendar Logic...")
    tool = LocalCalendarTool(path=TEMP_CAL)
    
    # 1. Add an event for TOMORROW
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    tomorrow_iso = tomorrow.isoformat()
    
    print(f"Adding event for: {tomorrow_iso}")
    tool.add_event("Test Meeting", tomorrow_iso)
    
    # 2. List events without parameters (should allow future?)
    print("\n[Test 1] List all events (no filters)")
    events_all = tool.list_events()
    print(f"Found {len(events_all)} events.")
    for e in events_all:
        print(f" - {e['name']} at {e['begin']}")
        
    if len(events_all) == 0:
        print("FAILURE: Event added but not found in simple list.")
        
    # 3. List events for "this week" (start=today, end=7 days from now)
    print("\n[Test 2] List events for this week")
    today_str = datetime.now().strftime('%Y-%m-%d')
    next_week_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"Filtering from {today_str} to {next_week_str}")
    events_week = tool.list_events(start=today_str, end=next_week_str)
    print(f"Found {len(events_week)} events.")
    
    if len(events_week) == 0:
        print("FAILURE: Event added but not found in filtered list.")
        
    # 4. List events with timezone mismatch potential
    # If I pass a date only "2026-02-14", does it catch "2026-02-14T10:00:00"?
    print("\n[Test 3] Date-only filter match")
    tomorrow_date_str = tomorrow.strftime('%Y-%m-%d')
    events_day = tool.list_events(start=tomorrow_date_str)
    print(f"Filtering for start={tomorrow_date_str} (implied day?)")
    print(f"Found {len(events_day)} events.")
    
    # Cleanup
    if os.path.exists(TEMP_CAL):
        os.remove(TEMP_CAL)

if __name__ == "__main__":
    test_calendar_logic()
