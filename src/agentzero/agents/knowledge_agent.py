import json
import re
from datetime import datetime
from dateutil import tz
from agentzero.agent_state import AgentState
from agentzero.llm_service import chat_completion

KNOWLEDGE_AGENT_PROMPT = """You are the Knowledge & Memory Specialist Agent.
Your job is to parse the user's request and generate a JSON execution plan for retrieving or storing facts and notes.

Available Tools:
1. 'remember_fact': Stores a new fact. Requires 'fact' (a clear, concise statement).
2. 'query_note': Searches notes. Requires 'query'.
3. 'get_file': Requires 'path'.

CRITICAL RULE FOR MISSING PARAMETERS:
If you need to use a tool (like 'remember_fact') but the user's request is too vague, use the 'ask_user' tool to clarify.
Example: {{"plan": [{{"type": "ask_user", "params": {{"question": "What specific fact would you like me to remember about this topic?"}}}}]}}

JSON FORMAT REQUIREMENT:
You must respond with ONLY a valid JSON object containing a "plan" array.
Example: {{"plan": [{{"type": "remember_fact", "params": {{"fact": "User prefers dark mode"}}}}]}}

DO NOT wrap the JSON in markdown blocks (e.g. ```json). DO NOT output any conversational text. ONLY raw JSON is allowed.
If you need to ask a question, put it inside the JSON using the 'ask_user' tool type instead of talking directly.

Current Temporal Context:
{date_context}
"""

async def knowledge_agent_node(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('knowledge_agent:entry', state)

    now = datetime.now(tz.tzlocal())
    
    date_context = (
        f"Temporal Context:\n"
        f"- Currently: {now.strftime('%A, %Y-%m-%d %H:%M')}"
    )
    
    system_prompt = KNOWLEDGE_AGENT_PROMPT.format(date_context=date_context)

    # Self-correction reflection injection
    if state.tool_results:
        last_result = state.tool_results[-1]
        for v in last_result.values():
            if isinstance(v, str) and v.startswith("Error:"):
                system_prompt += f"\n\nReflection on previous attempt: You tried to execute the user's request previously, but the tool failed with this error: '{v}'. Please analyze the error and output a new, corrected plan."

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
        state.plan = plan
    except Exception as e:
        state.plan = []
        state.error = f"Knowledge planner error: {str(e)}"
        state.step = "error_handler"
        return state

    state.step = "knowledge_agent"
    log_node('knowledge_agent:exit', state)
    return state
