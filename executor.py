"""
Executor node for AgentZero (LangGraph).
Executes planned actions using local tools/skills, updates state and collects results.
Handles 'chat' intent by generating a conversational response using the LLM.
"""

from agent_state import AgentState
from tools import load_tools
from skills import load_skills
import requests
from llm_service import chat_completion

TOOLS = load_tools()
SKILLS = load_skills()


def chat_with_llm(message: str, history: list = None, rag_context: list = None) -> str:
    system_prompt = "Your name is Ein. You are a helpful, productivity AI agent."
    if rag_context:
        system_prompt += "\n\nRelevant Context about the User:\n" + "\n".join([f"- {fact}" for fact in rag_context])
        
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    try:
        return chat_completion(messages=messages, stream=False, timeout=120)
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
            rag_context = state.context.get("rag") if state.context else None
            chat_response = chat_with_llm(user_message, state.chat_history, rag_context)
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
