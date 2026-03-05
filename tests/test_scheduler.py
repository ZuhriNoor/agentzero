import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
from agentzero.scheduler import Scheduler

@pytest.fixture
def mock_broadcast():
    return AsyncMock()

@pytest.fixture
def mock_list_events(mocker):
    return mocker.patch("agentzero.scheduler.LocalCalendarTool.list_events", return_value=[])

@pytest.mark.asyncio
async def test_check_reminders(mock_broadcast, mock_list_events):
    """
    Test that the scheduler triggers a reminder if it's within the 5-minute window
    and hasn't been sent before.
    """
    scheduler = Scheduler(broadcast_func=mock_broadcast)
    
    # Setup mock event 2 minutes from now
    now = datetime.now()
    event_time = now + timedelta(minutes=2)
    
    # Scheduler checks for events spanning [now, now + 5 minutes]
    mock_list_events.return_value = [
        {
            "id": "event-123",
            "name": "Quick standup",
            "begin": event_time.isoformat()
        }
    ]
    
    # Run the check
    await scheduler.check_reminders()
    
    # Verify the broadcast function was called
    mock_broadcast.assert_called_once()
    args, _ = mock_broadcast.call_args
    notification = args[0]
    
    assert "Reminder:" in notification
    assert "Quick standup" in notification
    
    unique_id = f"Quick standup_{event_time.isoformat()}"
    assert unique_id in scheduler.reminders_sent

@pytest.mark.asyncio
async def test_scheduler_ignores_already_sent_reminders(mock_broadcast, mock_list_events):
    scheduler = Scheduler(broadcast_func=mock_broadcast)
    
    now = datetime.now()
    event_time = now + timedelta(minutes=2)
    
    mock_list_events.return_value = [
        {
            "name": "Quick standup",
            "begin": event_time.isoformat()
        }
    ]
    # Pretend we already sent it
    unique_id = f"Quick standup_{event_time.isoformat()}"
    scheduler.reminders_sent[unique_id] = datetime.now().timestamp()
    
    await scheduler.check_reminders()
    
    # Expect NO call because it was already sent
    mock_broadcast.assert_not_called()

@pytest.mark.asyncio
async def test_scheduler_ignores_events_outside_window(mock_broadcast, mock_list_events):
    scheduler = Scheduler(broadcast_func=mock_broadcast)
    
    now = datetime.now()
    # 10 mins away, outside LOOKAHEAD window (60 mins by default, but let's test a past event instead to ensure no trigger)
    event_time = now - timedelta(minutes=10)
    
    mock_list_events.return_value = [
        {
            "id": "event-456",
            "name": "Future event",
            "begin": event_time.isoformat()
        }
    ]
    
    await scheduler.check_reminders()
    mock_broadcast.assert_not_called()
