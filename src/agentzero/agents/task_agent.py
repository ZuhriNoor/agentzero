import json
import re
from datetime import datetime, timedelta
from dateutil import tz
from agentzero.agent_state import AgentState
from agentzero.llm_service import chat_completion

TASK_AGENT_PROMPT = """You are the Task & Habit Specialist Agent.
Your job is to parse the user's request and generate a JSON execution plan for tasks or habits.

Available Tools:
1. 'add_task': Requires 'task' (name), optional 'deadline' (YYYY-MM-DD HH:MM).
2. 'list_tasks': No params.
3. 'edit_task': Requires 'old_name', optional 'new_name', optional 'new_deadline' (YYYY-MM-DD HH:MM).
4. 'complete_task': Requires 'task_name'.
5. 'add_habit': Requires 'name', 'frequency'.
6. 'list_habits': No params.
7. 'track_habit': Requires 'habit_name'.

CRITICAL RULE FOR MISSING PARAMETERS:
If you need to use a tool (like 'add_task' or 'edit_task') but are missing critical context (like they said "remind me to..." but didn't say when, OR if they said "change the deadline" but didn't state the new date), use the 'ask_user' tool to clarify.
Example: {{"plan": [{{"type": "ask_user", "params": {{"question": "What is the new deadline for the milk task?"}}}}]}}

JSON FORMAT REQUIREMENT:
You must respond with ONLY a valid JSON object containing a "plan" array.
Example: {{"plan": [{{"type": "add_task", "params": {{"task": "Buy milk"}}}}]}}

DO NOT wrap the JSON in markdown blocks (e.g. ```json). DO NOT output any conversational text. ONLY raw JSON is allowed.
If you need to ask a question, put it inside the JSON using the 'ask_user' tool type instead of talking directly.

Current Temporal Context:
{date_context}
"""

async def task_agent_node(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('task_agent:entry', state)

    now = datetime.now(tz.tzlocal())
    tomorrow = now + timedelta(days=1)
    
    date_context = (
        f"Temporal Context:\n"
        f"- Currently: {now.strftime('%A, %Y-%m-%d %H:%M')}\n"
        f"- Tomorrow: {tomorrow.strftime('%A, %Y-%m-%d')}"
    )
    
    system_prompt = TASK_AGENT_PROMPT.format(date_context=date_context)

    # Self-correction reflection injection
    if state.tool_results:
        last_result = state.tool_results[-1]
        for v in last_result.values():
            if isinstance(v, str) and v.startswith("Error:"):
                system_prompt += f"\n\nReflection on previous attempt: You tried to execute the user's request previously, but the tool failed with this error: '{v}'. Please analyze the error and output a new, corrected plan (e.g. fixing typos in the task name)."

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
        
        # Format task deadlines explicitly into ISO 8601
        for action in plan:
            if action.get("type") in ["add_task", "edit_task"]:
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
        state.error = f"Task planner error: {str(e)}"
        state.step = "error_handler"
        return state

    state.step = "task_agent"
    log_node('task_agent:exit', state)
    return state
