
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser, tz
from agentzero.tools.calendar import LocalCalendarTool

logger = logging.getLogger("agentzero.scheduler")

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
                    data = json.load(f)
                    if isinstance(data, list):
                        now_ts = datetime.now().timestamp()
                        return {item: now_ts for item in data}
                    return data
            except:
                return {}
        return {}

    def _save_reminders_sent(self):
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(self.reminders_sent, f)

    async def start(self, initial_delay=0):
        self.running = True
        self._last_error_msg = None
        self._consecutive_errors = 0
        logger.info(f"Scheduler started. Waiting {initial_delay}s before first check...")
        if initial_delay > 0:
            await asyncio.sleep(initial_delay)
            
        while self.running:
            try:
                self._prune_old_reminders()
                await self.check_reminders()
                # Reset error tracking on success
                if self._consecutive_errors > 0:
                    logger.info("Scheduler recovered after previous errors.")
                self._consecutive_errors = 0
                self._last_error_msg = None
            except RecursionError:
                # Fatal: do NOT log (logging itself may trigger the recursion).
                # Just back off hard and retry later.
                self._consecutive_errors += 1
                backoff = min(300, 60 * (2 ** self._consecutive_errors))  # max 5 min
                await asyncio.sleep(backoff)
                continue
            except Exception as e:
                err_msg = str(e)
                self._consecutive_errors += 1
                # Only log if it's a NEW error (not the same one repeating)
                if err_msg != self._last_error_msg:
                    logger.error(f"Error in scheduler loop: {e}")
                    self._last_error_msg = err_msg
                elif self._consecutive_errors == 5:
                    logger.error(f"Scheduler error repeating (suppressing further logs): {e}")
                # Exponential backoff: 60s, 120s, 240s... max 5 min
                backoff = min(300, 60 * (2 ** min(self._consecutive_errors - 1, 3)))
                await asyncio.sleep(backoff)
                continue
            await asyncio.sleep(60)

    def _prune_old_reminders(self, max_age_hours=24):
        """Removes reminders sent more than 24 hours ago to prevent unbound growth."""
        now = datetime.now().timestamp()
        cutoff = now - (max_age_hours * 3600)
        expired = [uid for uid, ts in self.reminders_sent.items() if ts < cutoff]
        if expired:
            for uid in expired:
                del self.reminders_sent[uid]
            self._save_reminders_sent()

    async def check_reminders(self):
        now = datetime.now()
        upcoming_window = now + timedelta(minutes=LOOKAHEAD_MINUTES)
        
        logger.debug(f"Checking at {now}. Window up to {upcoming_window}")
        
        today_str = now.strftime('%Y-%m-%d')
        tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        events = self.calendar.list_events(start=today_str, end=tomorrow_str)
        
        logger.debug(f"Found {len(events)} events for query {today_str} to {tomorrow_str}")

        # Check pending tasks as well
        from agentzero.memory import StructuredMemory
        tasks_data = StructuredMemory("data/tasks.json").load()
        pending_tasks = [t for t in tasks_data.get("tasks", []) if not t.get("completed", False) and t.get("deadline")]

        # Combine items to check
        items_to_check = []
        for e in events:
            items_to_check.append({
                "type": "event",
                "id": f"event_{e['name']}_{e['begin']}",
                "name": e['name'],
                "time_str": e['begin']
            })
            
        for t in pending_tasks:
            items_to_check.append({
                "type": "task",
                "id": f"task_{t['task']}_{t['deadline']}",
                "name": t['task'],
                "time_str": t['deadline']
            })

        for item in items_to_check:
            try:
                evt_time_str = item['time_str']
                evt_time = dateutil_parser.parse(evt_time_str)

                now_aware = datetime.now(tz.tzlocal())
                upcoming_window = now_aware + timedelta(minutes=60)

                if evt_time.tzinfo is None:
                    evt_time = evt_time.replace(tzinfo=tz.tzlocal())
                else:
                    evt_time = evt_time.astimezone(tz.tzlocal())
                
                logger.debug(f"Examining {item['type']} '{item['name']}': {evt_time} vs Now: {now_aware}")

                if now_aware < evt_time <= upcoming_window:
                    unique_id = item['id']
                    
                    if unique_id not in self.reminders_sent:
                        time_diff = int((evt_time - now_aware).total_seconds() / 60)
                        prefix = "📅 Event" if item['type'] == 'event' else "✅ Task"
                        message = f"🔔 Reminder: {prefix} '{item['name']}' is due in {time_diff} minutes."
                        
                        logger.info(f"Sending reminder for {item['type']} '{item['name']}' in {time_diff} mins")
                        await self.broadcast_func(message)
                        
                        self.reminders_sent[unique_id] = datetime.now().timestamp()
                        self._save_reminders_sent()
                    else:
                        logger.debug(f"Already sent reminder for {unique_id}")
                else:
                    logger.debug(f"Item not in window. Time diff: {(evt_time - now_aware).total_seconds() / 60:.0f} mins")

            except Exception as e:
                logger.error(f"Error checking {item.get('type')} {item.get('name')}: {e}", exc_info=True)

    def stop(self):
        self.running = False
