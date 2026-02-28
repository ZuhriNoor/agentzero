
import asyncio
import json
import os
from datetime import datetime, timedelta
from tools.calendar import LocalCalendarTool

REMINDERS_FILE = 'data/reminders_sent.json'
LOOKAHEAD_MINUTES = 60 # Check for events starting in the next X minutes

class Scheduler:
    def __init__(self, broadcast_func):
        self.broadcast_func = broadcast_func
        self.running = False
        self.calendar = LocalCalendarTool()
        self.reminders_sent = self._load_reminders_sent()

    def _load_reminders_sent(self):
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_reminders_sent(self):
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(list(self.reminders_sent), f)

    async def start(self, initial_delay=0):
        self.running = True
        print(f"Scheduler started. Waiting {initial_delay}s before first check...")
        if initial_delay > 0:
            await asyncio.sleep(initial_delay)
            
        while self.running:
            try:
                await self.check_reminders()
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
            await asyncio.sleep(60) # Check every minute

    async def check_reminders(self):

        # Look for events starting in the next LOOKAHEAD_MINUTES
        now = datetime.now()
        upcoming_window = now + timedelta(minutes=LOOKAHEAD_MINUTES)
        
        print(f"[Scheduler] Checking at {now}. Window up to {upcoming_window}")
        
        # We need to filter manually since list_events takes strings
        # Ideally execute list_events for "today" and filter in python
        today_str = now.strftime('%Y-%m-%d')
        tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        # Queries start of today to start of tomorrow (effectively covering 24h of today + margin)
        # We need a wider window because list_events end is inclusive/exclusive depending on time
        events = self.calendar.list_events(start=today_str, end=tomorrow_str)
        
        print(f"[Scheduler] Found {len(events)} events for query {today_str} to {tomorrow_str}")

        for event in events:
            try:
                # Parse event time using dateutil for robustness
                from dateutil import parser, tz
                
                evt_time_str = event['begin']
                evt_time = parser.parse(evt_time_str)
                
                # Get current time as Aware (Local System Time)
                now_aware = datetime.now(tz.tzlocal())
                upcoming_window = now_aware + timedelta(minutes=60)

                # Ensure evt_time is comparable (convert to local system time)
                # If naive, assume it implies local time
                if evt_time.tzinfo is None:
                    evt_time = evt_time.replace(tzinfo=tz.tzlocal())
                else:
                    evt_time = evt_time.astimezone(tz.tzlocal())
                
                print(f"[Scheduler] Examining '{event['name']}': {evt_time} vs Now: {now_aware}")

                # Check if event is within window (now < event < now+60m)
                if now_aware < evt_time <= upcoming_window:
                    # Construct unique ID for dedup: name + time
                    unique_id = f"{event['name']}_{event['begin']}"
                    
                    if unique_id not in self.reminders_sent:
                        time_diff = int((evt_time - now_aware).total_seconds() / 60)
                        message = f"🔔 Reminder: '{event['name']}' starts in {time_diff} minutes."
                        
                        print(f"Sending reminder: {message}")
                        await self.broadcast_func(message)
                        
                        self.reminders_sent.add(unique_id)
                        self._save_reminders_sent()
                    else:
                        print(f"[Scheduler] Already sent reminder for {unique_id}")
                else:
                     print(f"[Scheduler] Event not in window. Time diff: {(evt_time - now_aware).total_seconds() / 60} mins")


            except Exception as e:
                print(f"Error checking event {event.get('name')}: {e}")
                import traceback
                traceback.print_exc()

    def stop(self):
        self.running = False
