"""
Executor node for AgentZero (LangGraph).
Executes planned actions using local tools/skills, updates state and collects results.
Handles 'chat' intent by generating a conversational response using the LLM.
"""

from agent_state import AgentState
from tools import load_tools
from skills import load_skills
import requests
from ollama_config import OLLAMA_MODEL, OLLAMA_API_URL

TOOLS = load_tools()
SKILLS = load_skills()


def chat_with_llm(message: str) -> str:
    prompt = f"You are a helpful, privacy-preserving AI assistant.\nUser: {message}"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "[No response]")
    except Exception as e:
        return f"[Chat error: {str(e)}]"


def executor(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('executor:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('executor:error', state)
        return state
    results = []
    results = []
    
    # Check if we skipped planner (chat intent with no plan)
    if not state.plan and state.intent == "chat":
        # Generate a virtual plan for chat
        state.plan = [{"type": "chat", "params": state.user_input}]
        
    if not state.plan:
        state.error = "No plan to execute."
        state.step = "error_handler"
        return state
    for action in state.plan:
        action_type = action.get("type")
        params = action.get("params", {})
        # Handle chat intent
        if action_type == "chat":
            if isinstance(params, str):
                user_message = params
            else:
                user_message = params.get("message", state.user_input)
            chat_response = chat_with_llm(user_message)
            results.append({"chat": chat_response})
            continue
        # Check permissions
        if not state.permissions.get(action_type, False):
            results.append({"error": f"Permission denied for {action_type}"})
            continue
        # Execute tool or skill
        if action_type in TOOLS:
            try:
                result = TOOLS[action_type].run(**params)
                results.append({"tool": action_type, "result": result})
            except Exception as e:
                results.append({"tool": action_type, "error": str(e)})
        elif action_type in SKILLS:
            try:
                result = SKILLS[action_type].run(**params)
                results.append({"skill": action_type, "result": result})
            except Exception as e:
                results.append({"skill": action_type, "error": str(e)})
        else:
            results.append({"error": f"Unknown action type: {action_type}"})
    state.tool_results = results
    state.step = "executor"
    log_node('executor:exit', state)
    return state
