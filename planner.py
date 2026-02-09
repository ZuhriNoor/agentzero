"""
Planner node for AgentZero (LangGraph).
Generates multi-step plans using a local LLM via Ollama API, deterministic output.
Uses LLM to extract event details for scheduling intents.
"""

from agent_state import AgentState
import requests
import json
from datetime import datetime, timedelta
from memory import StructuredMemory
from ollama_config import OLLAMA_MODEL, OLLAMA_API_URL

# OLLAMA_API_URL and OLLAMA_MODEL are loaded from .env via ollama_config.py
HABIT_MEMORY_PATH = 'data/habits.json'

# Intents that require habits context
HABIT_INTENTS = {
    "plan_day", "plan_week", "list_habits", "add_habit", "delete_habit", "track_habit"
}

SCHEDULE_INTENTS = {"add_task", "add_event"}

PLANNER_SYSTEM_PROMPT = (
    "You are a deterministic task planner for a privacy-preserving AI agent. "
    "Given the user's intent and context, generate a step-by-step plan as a JSON array of actions. "
    "Each action should have a 'type' and 'params'. "
    "If the intent is 'chat', create a single action of type 'chat' with the user's message as a parameter. "
    "If the intent is 'add_task' or 'add_event', extract the event name, date, and time directly from the user's message and generate only an 'add_event' or 'add_task' action with those parameters. "
    "Do not generate a 'parse_message' action. "
    "Respond ONLY with a JSON object: {{\"plan\": [ ... ]}}"
    "\nFor scheduling, use the current date: {current_date}"
    "\nExamples:"
    "\nUser: I have a meeting tomorrow at 10:30 AM -> {{\"plan\": [{{\"type\": \"add_event\", \"params\": {{\"name\": \"meeting\", \"date\": \"2026-01-28\", \"time\": \"10:30\"}}}}]}}"
    "\nUser: add buy milk to my todos -> {{\"plan\": [{{\"type\": \"add_task\", \"params\": {{\"task\": \"buy milk\"}}}}]}}"
)

def load_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get('habits', [])

def planner(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('planner:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('planner:error', state)
        return state
    # Add habits to context only for relevant intents
    context = state.context or {}
    if (state.intent in HABIT_INTENTS) or (
        state.intent and any(x in state.intent for x in ["plan", "habit"])
    ):
        context = dict(context)  # copy
        context['habits'] = load_habits()
    # Add current date for LLM extraction
    current_date = datetime.now().strftime('%Y-%m-%d')
    prompt = PLANNER_SYSTEM_PROMPT.format(current_date=current_date)
    prompt = f"{prompt}\nIntent: {state.intent}\nContext: {json.dumps(context)}\nUser: {state.user_input}"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        if state.intent == "list_events":
            # Simple deterministic plan for listing events
            # Optionally parse date from user_input for filtering
            import re
            date_match = re.search(r"tomorrow|today|\d{1,2} \w+ \d{4}|\d{4}-\d{2}-\d{2}", state.user_input.lower())
            params = {}
            if date_match:
                # For 'tomorrow', calculate date
                if "tomorrow" in date_match.group():
                    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    params["start"] = tomorrow
                elif "today" in date_match.group():
                    today = datetime.now().strftime('%Y-%m-%d')
                    params["start"] = today
                else:
                    params["start"] = date_match.group()
            plan = [{"type": "list_events", "params": params}]
            state.plan = plan
        else:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            output = data.get("response", "{}")
            # Extract only the first valid JSON object from the output
            import re
            match = re.search(r'\{.*\}', output, re.DOTALL)
            json_str = match.group(0) if match else '{}'
            plan_data = json.loads(json_str)
            plan = plan_data.get("plan", [])
            # Post-process: for add_event, combine date and time into begin (ISO)
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
        state.error = f"Planner error: {str(e)}"
        state.step = "error_handler"
        log_node('planner:error', state)
        return state
    state.step = "planner"
    log_node('planner:exit', state)
    return state
