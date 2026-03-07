"""
Planner node for AgentZero (LangGraph).
Generates multi-step plans using a local LLM via Ollama API, deterministic output.
Uses LLM to extract event details for scheduling intents.
"""

from agentzero.agent_state import AgentState
import json
import re
from datetime import datetime, timedelta
from agentzero.memory import StructuredMemory
from agentzero.llm_service import generate_completion
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
    "If the intent is 'add_event', extract the event name, date, and time directly from the user's message and generate an 'add_event' action with those parameters. "
    "If the intent is 'add_task', extract the task name, and an optional 'deadline' (format: YYYY-MM-DD HH:MM) and generate an 'add_task' action. "
    "If the intent is 'list_tasks', generate a single 'list_tasks' action with no parameters. "
    "If the intent is 'edit_task', extract 'old_name', 'new_name' (optional), and 'new_deadline' (optional, YYYY-MM-DD HH:MM) and generate an 'edit_task' action. "
    "If the intent is 'complete_task', extract 'task_name' and generate a 'complete_task' action. "
    "If the intent is 'list_events', extract 'start' and 'end' dates if a range is specified. 'start' defaults to filter events FROM that time onwards. To list events for a specific day, PROVIDE BOTH 'start' (00:00) and 'end' (23:59) for that day. "
    "If the intent is 'remember_fact', extract the core fact to remember from the user's message and generate a 'remember_fact' action with a 'fact' parameter. "
    "If the intent is 'plan_day', generate a SINGLE 'plan_day' action with a 'date' parameter (YYYY-MM-DD). The action will fetch events, tasks, and habits internally. "
    "If the intent is 'plan_week', generate a SINGLE 'plan_week' action with a 'start_date' parameter (YYYY-MM-DD). The action will fetch events, tasks, and habits internally. "
    "Self-Correction: If the prompt contains a 'Reflection on previous attempt', you previously failed to execute the plan. Adjust your parameters (e.g. fix spelling/names) to succeed. "
    "Respond ONLY with a JSON object: {{\"plan\": [ ... ]}}"
    "\n{date_context}"
    "\nExamples:"
    "\nUser: I have a meeting tomorrow at 10:30 AM -> {{\"plan\": [{{\"type\": \"add_event\", \"params\": {{\"name\": \"meeting\", \"date\": \"2026-01-28\", \"time\": \"10:30\"}}}}]}}"
    "\nUser: Add buy milk to my todos by tomorrow 5 PM -> {{\"plan\": [{{\"type\": \"add_task\", \"params\": {{\"task\": \"buy milk\", \"deadline\": \"2026-01-28 17:00\"}}}}]}}"
    "\nUser: What tasks do I have pending? -> {{\"plan\": [{{\"type\": \"list_tasks\", \"params\": {{}}}}]}}"
    "\nUser: Complete the buy milk task -> {{\"plan\": [{{\"type\": \"complete_task\", \"params\": {{\"task_name\": \"buy milk\"}}}}]}}"
    "\nUser: What do I have this week? -> {{\"plan\": [{{\"type\": \"list_events\", \"params\": {{\"start\": \"2026-01-27\", \"end\": \"2026-02-03\"}}}}]}}"
    "\nUser: plan my day for tomorrow -> {{\"plan\": [{{\"type\": \"plan_day\", \"params\": {{\"date\": \"2026-01-28\"}}}}]}}"
)

def load_habits():
    mem = StructuredMemory(HABIT_MEMORY_PATH)
    data = mem.load()
    return data.get('habits', [])

async def planner(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
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
    # Add Explicit Date Context for LLM calculation
    now = datetime.now()
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
    
    prompt = PLANNER_SYSTEM_PROMPT.format(date_context=date_context)
    prompt = f"{prompt}\nIntent: {state.intent}\nContext: {json.dumps(context)}\nUser: {state.user_input}"
    
    # Self-correction reflection injection
    if state.tool_results:
        # Check if the last run resulted in an error
        last_result = state.tool_results[-1]
        for v in last_result.values():
            if isinstance(v, str) and v.startswith("Error:"):
                # Append reflection to the prompt
                reflection = f"\n\nReflection on previous attempt: You tried to execute the user's request previously, but the tool failed with this error: '{v}'. Please analyze the error and output a new, corrected plan (e.g. fixing typos in the task name or dates)."
                prompt += reflection

    try:
        output = await generate_completion(prompt=prompt, stream=False, timeout=30)
        
        # Extract only the first valid JSON object from the output
        match = re.search(r'\{.*\}', output, re.DOTALL)
        json_str = match.group(0) if match else '{}'
        plan_data = json.loads(json_str)
        plan = plan_data.get("plan", [])
        # Post-process: for add_event and add_task deadlines, format into ISO
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
            elif action.get("type") == "add_task" or action.get("type") == "edit_task":
                params = action.get("params", {})
                deadline = params.get("deadline") or params.get("new_deadline")
                if deadline:
                    try:
                        dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                        if action.get("type") == "add_task":
                            params["deadline"] = dt.isoformat()
                        else:
                            params["new_deadline"] = dt.isoformat()
                    except Exception:
                        pass # keep arbitrary string if parse fails
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
