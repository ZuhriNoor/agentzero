
import asyncio
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from dateutil import tz
from scheduler import Scheduler

async def test_scheduler():
    print("Testing Scheduler Logic...")
    
    # Mock broadcast function
    mock_broadcast = MagicMock()
    async def broadcast_wrapper(msg):
        print(f"[MOCK BROADCAST] {msg}")
        mock_broadcast(msg)

    # Initialize Scheduler
    s = Scheduler(broadcast_func=broadcast_wrapper)
    
    # Mock calendar.list_events
    # Create an event 30 minutes from now (Local Time)
    now_local = datetime.now(tz.tzlocal())
    event_time = now_local + timedelta(minutes=30)
    
    # Simulate list_events returning this event
    # list_events normally returns a dict with 'begin' as ISO string
    # We'll provide an ISO string that MIGHT look like what ICS returns
    # Case 1: Naive string (simulating old behavior or fallback)
    # Case 2: Aware string (simulating correct behavior)
    
    event_iso = event_time.isoformat()
    print(f"Injecting event at: {event_iso}")
    
    s.calendar.list_events = MagicMock(return_value=[
        {
            "name": "Test Meeting",
            "begin": event_iso,
            "end": (event_time + timedelta(hours=1)).isoformat(),
            "categories": []
        }
    ])
    
    # Run check_reminders
    await s.check_reminders()
    
    # Verify
    if mock_broadcast.called:
        print("\nSUCCESS: Broadcast was called.")
        args = mock_broadcast.call_args[0]
        print(f"Message: {args[0]}")
    else:
        print("\nFAILURE: Broadcast was NOT called.")

if __name__ == "__main__":
    asyncio.run(test_scheduler())
