import json
import re
from datetime import datetime, timedelta
from dateutil import tz
from agentzero.agent_state import AgentState
from agentzero.llm_service import chat_completion
from agentzero.memory import StructuredMemory

HABIT_MEMORY_PATH = 'data/habits.json'

def load_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get('habits', [])

CALENDAR_AGENT_PROMPT = """You are the Calendar Specialist Agent.
Your job is to parse the user's request (with its conversation history) and generate a specific JSON execution plan.

Available Tools:
1. 'add_event': Schedules an event. Requires 'name', 'date' (YYYY-MM-DD), 'time' (HH:MM).
2. 'list_events': Lists events. Requires 'start' and 'end' (YYYY-MM-DD). If listing a single day, provide BOTH start and end for that day.
3. 'plan_day': Plans a day combining events, habits, tasks. Requires 'date' (YYYY-MM-DD).
4. 'plan_week': Plans a week. Requires 'start_date' (YYYY-MM-DD).

CRITICAL RULE FOR MISSING PARAMETERS (Conversational Slot Filling):
If the user wants you to use a tool (like 'add_event') but they have NOT provided all required parameters (e.g. they didn't specify a time or date), DO NOT guess, fabricate, or pick a default!
Instead, use the 'ask_user' tool to ask them for the missing detail.
Example: {{"plan": [{{"type": "ask_user", "params": {{"question": "What time would you like to schedule the team meeting?"}}}}]}}

JSON FORMAT REQUIREMENT:
You must respond with ONLY a valid JSON object containing a "plan" array.
Example: {{"plan": [{{"type": "add_event", "params": {{"name": "Lunch", "date": "2026-02-15", "time": "12:00"}}}}]}}

DO NOT wrap the JSON in markdown blocks (e.g. ```json). DO NOT output any conversational text. ONLY raw JSON is allowed. 
If you need to ask a question, put it inside the JSON using the 'ask_user' tool type instead of talking directly.

Current Temporal Context:
{date_context}
"""

async def calendar_agent_node(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('calendar_agent:entry', state)

    now = datetime.now(tz.tzlocal())
    tomorrow = now + timedelta(days=1)
    day_after = now + timedelta(days=2)
    next_week = now + timedelta(days=7)
    
    date_context = (
        f"Temporal Context:\n"
        f"- Currently: {now.strftime('%A, %Y-%m-%d %H:%M')}\n"
        f"- Tomorrow: {tomorrow.strftime('%A, %Y-%m-%d')}\n"
        f"- Day after tomorrow: {day_after.strftime('%A, %Y-%m-%d')}\n"
        f"- Next week (same day): {next_week.strftime('%A, %Y-%m-%d')}"
    )
    
    system_prompt = CALENDAR_AGENT_PROMPT.format(date_context=date_context)
    
    # We provide the entire habit list if planning is involved
    if "plan" in state.user_input.lower():
        system_prompt += f"\n\nUser Habits (for planning reference):\n{json.dumps(load_habits())}"

    # Self-correction reflection injection
    if state.tool_results:
        last_result = state.tool_results[-1]
        for v in last_result.values():
            if isinstance(v, str) and v.startswith("Error:"):
                system_prompt += f"\n\nReflection on previous attempt: You tried to execute the user's request previously, but the tool failed with this error: '{v}'. Please analyze the error and output a new, corrected plan (e.g. fixing typos in dates or ranges)."

    messages = [{"role": "system", "content": system_prompt}]
    if state.chat_history:
        messages.extend(state.chat_history[-6:])
    messages.append({"role": "user", "content": state.user_input})

    try:
        output = await chat_completion(messages=messages, stream=False, timeout=30)
        match = re.search(r'\{.*\}', output, re.DOTALL)
        json_str = match.group(0) if match else '{}'
        plan_data = json.loads(json_str)
        plan = plan_data.get("plan", [])
        
        # Format datetimes specifically for calendar events
        for action in plan:
            if action.get("type") == "add_event":
                params = action.get("params", {})
                date = params.pop("date", None)
                time = params.pop("time", None)
                if date and time:
                    try:
                        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                        params["begin"] = dt.isoformat()
                    except Exception:
                        params["begin"] = f"{date}T{time}"
                elif date:
                    params["begin"] = date
                action["params"] = params
                
        state.plan = plan
    except Exception as e:
        state.plan = []
        state.error = f"Calendar planner error: {str(e)}"
        state.step = "error_handler"
        return state

    state.step = "calendar_agent"
    log_node('calendar_agent:exit', state)
    return state
