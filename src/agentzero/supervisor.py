import json
import re
from agentzero.agent_state import AgentState
from agentzero.llm_service import chat_completion

SUPERVISOR_PROMPT = """You are the Supervisor Router for a multi-agent system.
Your job is to route the user's request to the correct specialized sub-agent based on the conversation history.

Available Agents:
- 'calendar': Handles calendar events, daily/weekly planning, scheduling meetings, and time management.
- 'task': Handles todo lists, tasks, deadlines, and tracking habits.
- 'knowledge': Handles remembering facts, querying notes, and searching for information.
- 'chat': Handles general conversation, greetings, or when the user answers a question that doesn't belong to the other domains.

Analyze the user's latest input, alongside the context of the conversation history.
CRITICAL: If the user's latest input is a direct response to a clarifying question asked previously by a sub-agent (e.g. providing a time for an event, or a name for a task), YOU MUST route it to that same sub-agent domain so it can finish its job!

JSON FORMAT REQUIREMENT:
You must respond with ONLY a valid JSON object matching this schema:
{"domain": "calendar|task|knowledge|chat"}

DO NOT wrap the JSON in markdown blocks (e.g. ```json). DO NOT output any conversational text. ONLY raw JSON.
"""

async def supervisor_node(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('supervisor:entry', state)

    if state.error:
        state.step = "error_handler"
        log_node("supervisor:error", state)
        return state

    messages = [{"role": "system", "content": SUPERVISOR_PROMPT}]
    if state.chat_history:
        # Give it a good window of history to understand conversational context
        messages.extend(state.chat_history[-6:])
    messages.append({"role": "user", "content": state.user_input})

    try:
        output = await chat_completion(messages=messages, stream=False, timeout=10)
        match = re.search(r'\{.*\}', output, re.DOTALL)
        json_str = match.group(0) if match else '{}'
        data = json.loads(json_str)
        domain = data.get("domain", "chat").lower()
        
        valid_domains = {"calendar", "task", "knowledge", "chat"}
        if domain not in valid_domains:
            domain = "chat"
            
        state.intent = domain
    except Exception as e:
        state.intent = "chat" # Safe fallback

    state.step = "supervisor"
    log_node('supervisor:exit', state)
    return state
